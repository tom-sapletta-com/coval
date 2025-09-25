#!/usr/bin/env python3
"""
COVAL FastAPI Example - Complete Workflow Demonstration

This example shows how to use COVAL to:
1. Generate a FastAPI application
2. Deploy it with Docker
3. Simulate an error
4. Repair the application 
5. Deploy the fixed version

Usage:
    python examples/fastapi_example.py
"""

import os
import sys
import time
import tempfile
from pathlib import Path

# Add COVAL to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from coval.core.iteration_manager import IterationManager
from coval.core.cost_calculator import CostCalculator, CostMetrics
from coval.engines.generation_engine import GenerationEngine, GenerationRequest
from coval.engines.repair_engine import RepairEngine, LLMModel
from coval.docker.deployment_manager import DeploymentManager


def main():
    """Run the complete COVAL workflow example."""
    
    print("🤖 COVAL FastAPI Example - Complete Workflow")
    print("=" * 60)
    
    # Create example project directory
    example_dir = Path(__file__).parent / "temp_project"
    example_dir.mkdir(exist_ok=True)
    
    try:
        # Step 1: Initialize COVAL Components
        print("\n📋 Step 1: Initializing COVAL components...")
        
        iteration_manager = IterationManager(str(example_dir))
        cost_calculator = CostCalculator()
        generation_engine = GenerationEngine()
        deployment_manager = DeploymentManager(str(example_dir))
        
        print("✅ All components initialized successfully")
        
        # Step 2: Generate Initial FastAPI Application
        print("\n🚀 Step 2: Generating FastAPI application...")
        
        iteration_id = iteration_manager.create_iteration(
            description="FastAPI user management API",
            generation_type="generate"
        )
        
        generation_request = GenerationRequest(
            description="Create a FastAPI application with user registration, login, and profile management. Include SQLite database, Pydantic models, and proper error handling.",
            framework="fastapi",
            language="python",
            features=["authentication", "database", "pydantic", "error_handling"],
            constraints=[],
            existing_code=None
        )
        
        iteration_path = iteration_manager.get_iteration_path(iteration_id)
        
        # Simulate code generation (in real usage, this would call LLM)
        print(f"📁 Created iteration: {iteration_id}")
        print(f"📂 Iteration path: {iteration_path}")
        
        # Create example FastAPI code
        create_example_fastapi_code(iteration_path)
        
        # Update iteration status
        iteration_manager.update_iteration_status(
            iteration_id,
            'generated',
            confidence_score=0.85,
            files_changed=['main.py', 'models.py', 'auth.py', 'requirements.txt', 'Dockerfile']
        )
        
        print("✅ FastAPI application generated successfully")
        
        # Step 3: Cost Analysis Example
        print("\n💰 Step 3: Demonstrating cost analysis...")
        
        # Create sample metrics for cost calculation
        metrics = CostMetrics(
            lines_of_code=450,
            complexity_score=3.2,
            technical_debt=15.0,
            test_coverage=0.75,
            dependencies_count=5,
            modification_scope=0.4,
            historical_success_rate=0.0,  # New project
            iteration_count=1,
            framework_maturity=0.9,  # FastAPI is mature
            team_familiarity=0.8
        )
        
        cost_analysis = cost_calculator.calculate_cost(metrics)
        
        print(f"📊 Cost Analysis Results:")
        print(f"   Modify existing cost: {cost_analysis.modify_cost:.2f}")
        print(f"   Generate new cost: {cost_analysis.generate_cost:.2f}")
        print(f"   Recommendation: {cost_analysis.recommended_action}")
        print(f"   Confidence: {cost_analysis.confidence:.1%}")
        print(f"   Success probability: {cost_analysis.success_probability:.1%}")
        print(f"   Estimated time: {cost_analysis.estimated_time_hours:.1f} hours")
        
        # Step 4: Deployment Simulation
        print("\n🐳 Step 4: Simulating Docker deployment...")
        
        # In a real scenario, this would create actual Docker containers
        print(f"🏗️  Building Docker image for {iteration_id}")
        print(f"🚀 Deploying container on port 8000")
        print(f"🌐 Application available at http://localhost:8000")
        print("✅ Deployment simulation completed")
        
        # Step 5: Error Simulation and Repair
        print("\n🔧 Step 5: Simulating error and repair process...")
        
        # Create a simulated error log
        error_file = create_sample_error_log(iteration_path)
        
        # Initialize repair engine
        repair_engine = RepairEngine(model=LLMModel.QWEN_CODER)
        
        # Perform triage (analysis)
        print("🔍 Analyzing problem...")
        try:
            # In real usage, this would perform actual triage
            print("📊 Problem category: import_error")
            print("📈 Historical success rate: 0% (new system)")
            print("🎯 Repair recommendation: MODIFY (low complexity)")
            print("✅ Triage completed")
            
            # Create repair iteration
            repair_iteration_id = iteration_manager.create_iteration(
                description=f"Repair import error in {iteration_id}",
                generation_type="repair", 
                parent_iteration=iteration_id
            )
            
            repair_iteration_path = iteration_manager.get_iteration_path(repair_iteration_id)
            
            # Simulate repair (copy original + fix)
            create_repaired_code(iteration_path, repair_iteration_path)
            
            iteration_manager.update_iteration_status(
                repair_iteration_id,
                'repaired',
                success_rate=0.95
            )
            
            print(f"✅ Repair completed! New iteration: {repair_iteration_id}")
            
        except Exception as e:
            print(f"⚠️  Repair simulation skipped: {e}")
        
        # Step 6: Show Project Status
        print("\n📊 Step 6: Final project status...")
        
        print(f"📁 Total iterations: {len(iteration_manager.iterations)}")
        for iid, info in iteration_manager.iterations.items():
            print(f"   {iid}: {info.status} - {info.description}")
        
        print("\n🎉 COVAL workflow example completed successfully!")
        print("\nKey takeaways:")
        print("• COVAL manages iterative code generation and repair")
        print("• Each iteration is versioned and tracked")
        print("• Cost analysis helps decide between modify vs generate")
        print("• Docker deployments provide isolated environments")
        print("• Automated repair reduces manual debugging time")
        
    finally:
        # Cleanup
        print(f"\n🧹 Cleaning up example directory: {example_dir}")
        import shutil
        if example_dir.exists():
            shutil.rmtree(example_dir)


def create_example_fastapi_code(iteration_path: Path):
    """Create example FastAPI application files."""
    
    # Create main.py
    main_py = iteration_path / "main.py"
    main_py.write_text('''
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
import hashlib
import sqlite3

app = FastAPI(title="User Management API", version="1.0.0")

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./users.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

Base.metadata.create_all(bind=engine)

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    
    class Config:
        from_attributes = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "user-management-api"}

@app.post("/users/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # Hash password
    hashed_password = hashlib.sha256(user.password.encode()).hexdigest()
    
    db_user = User(
        username=user.username,
        email=user.email, 
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''.strip())
    
    # Create requirements.txt
    requirements = iteration_path / "requirements.txt"
    requirements.write_text('''
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
python-multipart==0.0.6
'''.strip())
    
    # Create Dockerfile
    dockerfile = iteration_path / "Dockerfile"
    dockerfile.write_text('''
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
'''.strip())
    
    print(f"📄 Created {len(list(iteration_path.glob('*')))} files in iteration")


def create_sample_error_log(iteration_path: Path) -> Path:
    """Create a sample error log for repair demonstration."""
    error_file = iteration_path / "error.log"
    error_file.write_text('''
Traceback (most recent call last):
  File "/app/main.py", line 4, in <module>
    from missing_module import some_function
ModuleNotFoundError: No module named 'missing_module'

Error occurred while starting FastAPI application.
The import statement is trying to import a non-existent module.
This is a common error when dependencies are not properly installed
or when there are typos in import statements.

Stack trace indicates the error is in main.py line 4.
'''.strip())
    
    return error_file


def create_repaired_code(original_path: Path, repair_path: Path):
    """Create repaired version of the code."""
    
    # Copy all files from original to repair path
    import shutil
    shutil.copytree(original_path, repair_path, dirs_exist_ok=True)
    
    # Fix the main.py file by removing the problematic import
    main_py = repair_path / "main.py"
    content = main_py.read_text()
    
    # Remove the problematic line (this would be done by LLM in real usage)
    fixed_content = content.replace(
        'from missing_module import some_function', 
        '# Fixed: Removed invalid import'
    )
    
    main_py.write_text(fixed_content)
    print("🔧 Applied repair: Removed invalid import statement")


if __name__ == "__main__":
    main()
