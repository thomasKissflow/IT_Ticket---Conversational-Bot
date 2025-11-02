#!/usr/bin/env python3
"""
Setup script to ensure demo environment is ready
"""

import os
import sys
from pathlib import Path

def check_environment():
    """Check if the environment is properly set up."""
    
    print("🔍 Checking Demo Environment...")
    
    # Check .env file
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found")
        print("   Please create .env with your AWS credentials")
        return False
    
    # Check required environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ['AWS_REGION']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    # Check if we can import required modules
    try:
        from agents.supervisor_agent import SupervisorAgent
        from agents.ticket_agent import TicketAgent
        from agents.knowledge_agent import KnowledgeAgent
        print("✅ All agent modules available")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Check data files
    data_files = [
        "../support-tickets.csv",
        "../product-documentation.pdf"
    ]
    
    for file_path in data_files:
        if not Path(file_path).exists():
            print(f"⚠️  Data file not found: {file_path}")
            print("   Demo will work but with limited data")
    
    print("✅ Environment check completed")
    return True

def create_sample_data():
    """Create sample data if real data files are missing."""
    
    # Create sample tickets CSV if missing
    tickets_file = Path("../support-tickets.csv")
    if not tickets_file.exists():
        print("📝 Creating sample tickets data...")
        
        sample_tickets = """id,title,description,status,priority,assignee,created_date,updated_date
TKT-2024-001,Login Issues,User cannot access dashboard after password reset,Open,High,Sarah Johnson,2024-01-15,2024-01-16
TKT-2024-002,Mobile App Crash,App crashes on startup for iOS users,In Progress,Critical,Mike Chen,2024-01-14,2024-01-17
TKT-2024-003,Email Notifications,Users not receiving email notifications,Resolved,Medium,Sarah Johnson,2024-01-13,2024-01-18
TKT-2024-004,Performance Issues,Dashboard loading slowly during peak hours,Open,High,Alex Rodriguez,2024-01-16,2024-01-16
TKT-2024-005,Feature Request,Add dark mode to mobile application,Backlog,Low,Product Team,2024-01-12,2024-01-12"""
        
        with open(tickets_file, 'w') as f:
            f.write(sample_tickets)
        
        print(f"✅ Sample tickets created: {tickets_file}")

def main():
    """Main setup function."""
    
    print("🚀 DEMO SETUP - Agentic Voice Assistant")
    print("=" * 50)
    
    if not check_environment():
        print("\n❌ Environment setup incomplete")
        print("Please fix the issues above before running the demo")
        return False
    
    create_sample_data()
    
    print("\n✅ Demo environment is ready!")
    print("\nNext steps:")
    print("1. Run the demo: python run_demo.py")
    print("2. Generate presentation summary: python generate_presentation_summary.py")
    print("\n🎯 Perfect for your judge presentation!")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)