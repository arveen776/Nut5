import json
import os
import re
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

#heooo
# Load environment variables from .env file
# Get the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path=env_path)

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables. Please create a .env file with your API key.")
client = OpenAI(api_key=api_key)

KNOWLEDGE_FILE = "knowledge.json"

def load_knowledge():
    """Load information from knowledge file"""
    if os.path.exists(KNOWLEDGE_FILE):
        try:
            with open(KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Handle migration from old format
                if "information" in data and "lots" not in data:
                    data = migrate_old_format(data)
                return data
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {KNOWLEDGE_FILE}: {e}")
            return {"lots": [], "last_updated": None}
        except Exception as e:
            print(f"Error reading {KNOWLEDGE_FILE}: {e}")
            return {"lots": [], "last_updated": None}
    return {"lots": [], "last_updated": None}

def migrate_old_format(data):
    """Migrate from old string format to new structured format"""
    lots = []
    for info in data.get("information", []):
        # Try to parse old format
        lot_match = re.search(r'Lot\s+(\d+)', info)
        if lot_match:
            lot_num = lot_match.group(1)
            status_match = re.search(r'Status:\s*([^,]+)', info)
            location_match = re.search(r'Location:\s*([^,]+)', info)
            date_match = re.search(r'Next Appointment Date:\s*([^,]+)', info)
            task_match = re.search(r'Task:\s*(.+)', info)
            
            lots.append({
                "lot_number": lot_num,
                "status": status_match.group(1).strip() if status_match else "Unknown",
                "location": location_match.group(1).strip() if location_match else "Unknown",
                "next_appointment_date": date_match.group(1).strip() if date_match else None,
                "task": task_match.group(1).strip() if task_match else None
            })
    return {"lots": lots, "last_updated": data.get("last_updated")}

def save_knowledge(data):
    """Save information to knowledge file"""
    try:
        data["last_updated"] = datetime.now().isoformat()
        with open(KNOWLEDGE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        raise Exception(f"Error saving knowledge file: {e}")

def format_lots_for_display(lots):
    """Format lots for display"""
    if not lots:
        return "No lots stored yet."
    
    formatted = []
    for lot in lots:
        line = f"Lot {lot['lot_number']}, Status: {lot['status']}, Location: {lot['location']}"
        if lot.get('next_appointment_date'):
            line += f", Next Appointment: {lot['next_appointment_date']}"
        if lot.get('task'):
            line += f", Task: {lot['task']}"
        formatted.append(line)
    return "\n".join(formatted)

def get_ai_decision(question, lots):
    """Get AI decision based on question and existing knowledge"""
    # Build context from lots
    lots_text = format_lots_for_display(lots)
    
    prompt = f"""You are an AI coordinator that manages construction lot information.

Current stored lots:
{lots_text if lots else "No lots stored yet."}

User question/input: {question}

IMPORTANT: You must respond in this EXACT format:

DECISION: [Give a SHORT, DIRECT answer. If asked about specific lots, just state the facts concisely. Example: "Lot 1001: Foundation Complete. Lot 1002: Framing In Progress." Keep it brief and to the point.]

NEW_LOT: [If a new lot should be added, provide in this EXACT format:
lot_number: [number]
status: [status]
location: [location]
next_appointment_date: [YYYY-MM-DD or null]
task: [task description or null]
If no new lot, write "none"]

UPDATE_LOT: [If an existing lot should be updated, provide in this EXACT format:
lot_number: [number]
status: [new status or "keep" to keep current]
location: [new location or "keep" to keep current]
next_appointment_date: [new date YYYY-MM-DD or "keep" or null]
task: [new task or "keep" to keep current or null]
If no update needed, write "none"]

Keep your DECISION answer SHORT and DIRECT. Answer only what is asked, nothing more.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a precise AI coordinator that manages construction lot information. Always respond in the exact format specified, with specific details."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def parse_structured_lot(text, section_name):
    """Parse structured lot information from AI response"""
    if not text or text.lower() == "none":
        return None
    
    lot = {}
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip()
            
            if key == "lot_number":
                lot["lot_number"] = value
            elif key == "status":
                lot["status"] = value if value.lower() != "keep" else None
            elif key == "location":
                lot["location"] = value if value.lower() != "keep" else None
            elif key == "next_appointment_date":
                lot["next_appointment_date"] = value if value.lower() not in ["keep", "null", "none"] else None
            elif key == "task":
                lot["task"] = value if value.lower() not in ["keep", "null", "none"] else None
    
    return lot if lot else None

def parse_ai_response(ai_response):
    """Parse AI response to extract decision, new lot, and updates"""
    decision = ""
    new_lot = None
    update_lot = None
    
    sections = {
        "DECISION:": "decision",
        "NEW_LOT:": "new_lot",
        "UPDATE_LOT:": "update_lot"
    }
    
    current_section = None
    section_content = {s: [] for s in sections.values()}
    
    lines = ai_response.split('\n')
    
    for line in lines:
        line_stripped = line.strip()
        
        # Check if this line starts a new section
        found_section = False
        for section_key, section_name in sections.items():
            if line_stripped.startswith(section_key):
                current_section = section_name
                # Extract content after the section header
                content = line_stripped.replace(section_key, "").strip()
                if content:
                    section_content[section_name].append(content)
                found_section = True
                break
        
        if not found_section and current_section:
            if line_stripped:
                section_content[current_section].append(line_stripped)
    
    # Process sections
    decision = " ".join(section_content["decision"]).strip()
    
    new_lot_text = "\n".join(section_content["new_lot"])
    new_lot = parse_structured_lot(new_lot_text, "new_lot")
    
    update_lot_text = "\n".join(section_content["update_lot"])
    update_lot = parse_structured_lot(update_lot_text, "update_lot")
    
    return decision, new_lot, update_lot

def update_knowledge(knowledge, new_lot, update_lot):
    """Update knowledge file with new or updated lot information"""
    lots = knowledge.get("lots", [])
    
    # Add new lot
    if new_lot and new_lot.get("lot_number"):
        # Check if lot already exists
        existing = next((l for l in lots if l["lot_number"] == new_lot["lot_number"]), None)
        if not existing:
            lots.append({
                "lot_number": new_lot["lot_number"],
                "status": new_lot.get("status", "Unknown"),
                "location": new_lot.get("location", "Unknown"),
                "next_appointment_date": new_lot.get("next_appointment_date"),
                "task": new_lot.get("task")
            })
        else:
            # Update existing lot with new info
            for key in ["status", "location", "next_appointment_date", "task"]:
                if new_lot.get(key) is not None:
                    existing[key] = new_lot[key]
    
    # Update existing lot
    if update_lot and update_lot.get("lot_number"):
        lot_num = update_lot["lot_number"]
        existing = next((l for l in lots if l["lot_number"] == lot_num), None)
        
        if existing:
            for key in ["status", "location", "next_appointment_date", "task"]:
                if update_lot.get(key) is not None:
                    existing[key] = update_lot[key]
        else:
            # If lot doesn't exist, create it
            lots.append({
                "lot_number": lot_num,
                "status": update_lot.get("status", "Unknown"),
                "location": update_lot.get("location", "Unknown"),
                "next_appointment_date": update_lot.get("next_appointment_date"),
                "task": update_lot.get("task")
            })
    
    knowledge["lots"] = lots
    return knowledge

def display_lots(lots):
    """Display lots in a formatted table"""
    if not lots:
        print("\nNo lots stored yet.")
        return
    
    print("\n" + "=" * 100)
    print(f"{'Lot #':<10} {'Status':<25} {'Location':<15} {'Next Appointment':<18} {'Task':<30}")
    print("=" * 100)
    
    for lot in lots:
        # Safely get values and handle None
        lot_num = str(lot.get("lot_number") or "N/A")
        status = str(lot.get("status") or "N/A")
        location = str(lot.get("location") or "N/A")
        appointment = str(lot.get("next_appointment_date") or "N/A")
        task = str(lot.get("task") or "N/A")
        
        # Truncate long strings to fit columns
        lot_num = lot_num[:9] if len(lot_num) > 9 else lot_num
        status = status[:24] if len(status) > 24 else status
        location = location[:14] if len(location) > 14 else location
        appointment = appointment[:17] if len(appointment) > 17 else appointment
        task = task[:29] if len(task) > 29 else task
        
        print(f"{lot_num:<10} {status:<25} {location:<15} {appointment:<18} {task:<30}")
    
    print("=" * 100)

def main():
    """Main interactive loop"""
    print("AI Lot Information Coordinator")
    print("Type 'quit' to exit\n")
    
    try:
        while True:
            # Load current knowledge
            try:
                knowledge = load_knowledge()
                lots = knowledge.get("lots", [])
            except Exception as e:
                print(f"Error loading knowledge: {e}")
                knowledge = {"lots": [], "last_updated": None}
                lots = []
            
            # Get user input
            try:
                question = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if not question:
                continue
            
            # Get AI decision
            try:
                ai_response = get_ai_decision(question, lots)
            except Exception as e:
                print(f"Error: {e}")
                continue
            
            # Parse response
            try:
                decision, new_lot, update_lot = parse_ai_response(ai_response)
            except Exception as e:
                decision = ai_response
                new_lot = None
                update_lot = None
            
            # Display decision - just the answer, nothing else
            if decision:
                print(decision)
            else:
                print(ai_response)
            
            # Update knowledge if needed (silently)
            try:
                if new_lot:
                    knowledge = update_knowledge(knowledge, new_lot, None)
                    save_knowledge(knowledge)
                
                if update_lot:
                    knowledge = update_knowledge(knowledge, None, update_lot)
                    save_knowledge(knowledge)
            except Exception as e:
                print(f"Error updating knowledge: {e}")
            
            print()  # Empty line for spacing
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
