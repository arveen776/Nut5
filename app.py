from flask import Flask, render_template, request, jsonify
from ai_test import (
    load_knowledge, save_knowledge, get_ai_decision, 
    parse_ai_response, update_knowledge
)

app = Flask(__name__)

@app.route('/')
def index():
    """Main page"""
    knowledge = load_knowledge()
    lots = knowledge.get("lots", [])
    return render_template('index.html', lots=lots)

@app.route('/api/query', methods=['POST'])
def query():
    """Handle AI queries"""
    try:
        data = request.json
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'error': 'Question is required'}), 400
        
        # Load current knowledge
        knowledge = load_knowledge()
        lots = knowledge.get("lots", [])
        
        # Get AI decision
        ai_response = get_ai_decision(question, lots)
        
        # Parse response
        decision, new_lot, update_lot = parse_ai_response(ai_response)
        
        # Update knowledge if needed
        updated = False
        if new_lot:
            knowledge = update_knowledge(knowledge, new_lot, None)
            save_knowledge(knowledge)
            updated = True
        
        if update_lot:
            knowledge = update_knowledge(knowledge, None, update_lot)
            save_knowledge(knowledge)
            updated = True
        
        # Reload lots if updated
        if updated:
            knowledge = load_knowledge()
            lots = knowledge.get("lots", [])
        
        return jsonify({
            'answer': decision if decision else ai_response,
            'lots': lots,
            'updated': updated
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/lots', methods=['GET'])
def get_lots():
    """Get current lots"""
    try:
        knowledge = load_knowledge()
        lots = knowledge.get("lots", [])
        return jsonify({'lots': lots})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
