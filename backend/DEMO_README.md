# 🎯 Agentic Voice Assistant - Demo Test Suite

## Overview
This demo showcases the multi-agent AI system's capabilities through 5 carefully designed test scenarios. Perfect for presentations to judges, investors, or stakeholders.

## 🚀 Quick Start

### 1. Setup Environment
```bash
# Ensure you're in the backend directory
cd backend

# Run setup check
python setup_demo.py
```

### 2. Run Demo Tests
```bash
# Execute the full demo suite
python run_demo.py
```

### 3. Generate Presentation Summary
```bash
# Create presentation-ready output
python generate_presentation_summary.py
```

## 📊 What the Demo Tests

### Test Scenarios

1. **Ticket Lookup** - `"What's the status of ticket TKT-2024-001?"`
   - Tests direct ticket retrieval
   - Expected: SupervisorAgent → TicketAgent
   - Measures: Response time, data accuracy

2. **Knowledge Base Query** - `"How do I reset my password in the system?"`
   - Tests documentation search
   - Expected: SupervisorAgent → KnowledgeAgent
   - Measures: Intent classification, knowledge retrieval

3. **Complex Ticket Search** - `"Show me all high priority tickets assigned to Sarah Johnson"`
   - Tests multi-criteria filtering
   - Expected: SupervisorAgent → TicketAgent
   - Measures: Query complexity handling

4. **Hybrid Query** - `"What are the system requirements for the mobile app and also check if there are any related tickets?"`
   - Tests multi-agent coordination
   - Expected: SupervisorAgent → KnowledgeAgent + TicketAgent
   - Measures: Agent orchestration, parallel processing

5. **Support Request** - `"I'm having trouble with login errors, can you help troubleshoot?"`
   - Tests ambiguous query handling
   - Expected: SupervisorAgent → KnowledgeAgent + TicketAgent
   - Measures: Intent disambiguation, comprehensive response

## 📈 Key Metrics Measured

### Performance Metrics
- **Response Time**: Total time from query to response
- **Agent Execution Time**: Individual agent processing times
- **Routing Accuracy**: Correct agent selection percentage
- **Overall Confidence**: AI confidence in responses
- **Success Rate**: Percentage of successful completions

### System Capabilities
- **Multi-Agent Coordination**: Parallel agent execution
- **Intent Classification**: Query understanding accuracy
- **Error Handling**: Graceful failure management
- **Scalability**: Performance under different query types

## 🎤 Presentation Highlights

### For Judges/Investors
- **Innovation**: Multi-agent architecture with intelligent routing
- **Performance**: Sub-second response times for most queries
- **Reliability**: High success rates and confidence scores
- **Scalability**: Cloud-native AWS architecture

### Technical Excellence
- **AI Integration**: AWS Bedrock with Claude models
- **Real-time Processing**: WebSocket communication
- **Performance Optimization**: Response time monitoring
- **Enterprise Ready**: Production-grade error handling

## 📋 Output Files

After running the demo, you'll get:

1. **`demo_test_report.json`** - Detailed technical metrics
2. **`presentation_slide_data.json`** - Data formatted for slides
3. **Console output** - Real-time performance display

## 🔧 Customization

### Adding New Test Cases
Edit `demo_test.py` and add to the `test_questions` list:

```python
{
    "id": 6,
    "question": "Your custom question here",
    "type": "Custom Query Type",
    "expected_agents": ["SupervisorAgent", "TicketAgent"],
    "description": "Description of what this tests"
}
```

### Modifying Metrics
Update the `_generate_summary_report()` method in `DemoTestRunner` to add custom metrics.

## 🎯 Judge Presentation Tips

### Key Talking Points
1. **Multi-Agent Intelligence**: Show how different agents specialize
2. **Real-Time Performance**: Highlight sub-second response times
3. **Routing Accuracy**: Demonstrate intelligent query understanding
4. **Scalability**: Explain cloud-native architecture benefits

### Demo Flow Suggestion
1. Run live demo showing console output
2. Highlight key metrics as they appear
3. Show final summary with performance highlights
4. Discuss technical architecture and business impact

## 🛠️ Troubleshooting

### Common Issues

**Import Errors**
```bash
# Ensure you're in the backend directory
cd backend
# Check Python path
python -c "import sys; print(sys.path)"
```

**AWS Credentials**
```bash
# Check .env file exists and has AWS_REGION
cat .env
# Test AWS connection
python test_aws.py
```

**Missing Data Files**
- Demo creates sample data automatically
- For full functionality, ensure `support-tickets.csv` and `product-documentation.pdf` exist

### Performance Optimization
- Ensure stable internet connection for AWS API calls
- Run on a machine with adequate resources
- Close unnecessary applications during demo

## 📞 Support

For issues or questions about the demo:
1. Check the main project README
2. Verify environment setup with `setup_demo.py`
3. Review error messages in console output

---

**Perfect for showcasing your Agentic Voice Assistant to judges! 🏆**