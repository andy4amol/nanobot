"""FastAPI application for nanobot multi-tenant C端 service.

This module provides REST API endpoints for managing users, generating reports,
and handling real-time chat with the AI assistant.
"""

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

# Import nanobot components
from nanobot.workspace.manager import WorkspaceManager
from nanobot.services.user_config import UserConfigManager, UserConfig, UserWatchlist, UserPreferences
from nanobot.agent.multi_tenant_loop import MultiTenantAgentLoop
from nanobot.bus.queue import MessageBus
from nanobot.providers.litellm_provider import LiteLLMProvider
from nanobot.config.loader import load_config

# Import scheduler
from nanobot.services.scheduler import ReportScheduler

# Import logger
from loguru import logger

# Security
security = HTTPBearer()

# Global instances
workspace_manager: Optional[WorkspaceManager] = None
config_manager: Optional[UserConfigManager] = None
report_scheduler: Optional[ReportScheduler] = None
agent_loop: Optional[Any] = None  # Agent loop for LLM processing

# Pydantic models for API requests/responses

class UserCreate(BaseModel):
    """Request model for creating a new user."""
    user_id: str = Field(..., description="Unique user identifier", min_length=3, max_length=50)
    initial_data: Optional[Dict[str, Any]] = Field(default=None, description="Initial custom data")


class UserResponse(BaseModel):
    """Response model for user information."""
    user_id: str
    created_at: str
    updated_at: str
    watchlist: Dict[str, Any]
    preferences: Dict[str, Any]
    custom_data: Dict[str, Any]

    class Config:
        from_attributes = True


class WatchlistUpdate(BaseModel):
    """Request model for updating watchlist."""
    stocks: Optional[List[str]] = Field(default=None, description="List of stock symbols to watch")
    influencers: Optional[List[str]] = Field(default=None, description="List of influencer accounts to follow")
    keywords: Optional[List[str]] = Field(default=None, description="Keywords to track")
    sectors: Optional[List[str]] = Field(default=None, description="Industry sectors of interest")


class PreferencesUpdate(BaseModel):
    """Request model for updating preferences."""
    report_frequency: Optional[str] = Field(default=None, description="Report frequency: daily, weekly, realtime, both")
    report_time: Optional[str] = Field(default=None, description="Time for report generation (HH:MM)")
    report_format: Optional[str] = Field(default=None, description="Report format: markdown, pdf, html")
    language: Optional[str] = Field(default=None, description="Language preference: zh, en")
    max_report_length: Optional[int] = Field(default=None, description="Maximum report length")
    notification_channels: Optional[List[str]] = Field(default=None, description="Notification channels: push, email, wechat")


class ChatRequest(BaseModel):
    """Request model for chat messages."""
    message: str = Field(..., description="Message content", min_length=1, max_length=10000)
    session_id: Optional[str] = Field(default=None, description="Session identifier for maintaining context")


class ChatResponse(BaseModel):
    """Response model for chat messages."""
    response: str
    session_id: str
    user_id: str
    processing_time_ms: Optional[int] = None


class ReportRequest(BaseModel):
    """Request model for generating reports."""
    report_type: str = Field(default="daily", description="Type of report: daily, weekly, custom")
    custom_prompt: Optional[str] = Field(default=None, description="Custom prompt for report generation")
    focus_areas: Optional[List[str]] = Field(default=None, description="Specific areas to focus on")


class ReportResponse(BaseModel):
    """Response model for report generation."""
    report_id: str
    user_id: str
    status: str
    message: str
    estimated_completion_time: Optional[str] = None


class ReportStatus(BaseModel):
    """Response model for report status."""
    report_id: str
    user_id: str
    status: str  # pending, processing, completed, failed
    progress: Optional[int] = None  # 0-100
    content: Optional[str] = None  # Only if completed
    error_message: Optional[str] = None  # Only if failed
    created_at: str
    completed_at: Optional[str] = None


class ScheduleInfo(BaseModel):
    """Response model for user schedule information."""
    user_id: str
    daily_report: Dict[str, Any]
    weekly_report: Dict[str, Any]
    next_scheduled_jobs: List[Dict[str, Any]]


class HealthCheck(BaseModel):
    """Response model for health check."""
    status: str
    timestamp: str
    version: str
    services: Dict[str, Any]


# FastAPI app setup

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global workspace_manager, config_manager, report_scheduler, agent_loop
    
    print("=" * 60)
    print("Starting nanobot Multi-Tenant Service")
    print("=" * 60)
    
    # Initialize workspace manager
    print("\n[1] Initializing Workspace Manager...")
    workspace_manager = WorkspaceManager("~/.nanobot/workspaces")
    print("  ✓ Workspace Manager initialized")
    
    # Initialize config manager
    print("\n[2] Initializing User Config Manager...")
    config_manager = UserConfigManager("~/.nanobot/workspaces")
    print("  ✓ User Config Manager initialized")
    
    # Initialize LLM provider and agent loop for real report generation
    print("\n[3] Initializing LLM Provider & Agent Loop...")
    agent_loop = None
    llm_provider = None
    message_bus = None
    try:
        from nanobot.providers.litellm_provider import LiteLLMProvider
        from nanobot.agent.multi_tenant_loop import MultiTenantAgentLoop
        from nanobot.bus.queue import MessageBus
        
        # Initialize Gemini LLM provider
        # Get API key from environment or use the provided one
        gemini_api_key = "AIzaSyCoBZlzOKBCAJ44MmMZe3rSKYnWL7lW_lo"
        
        if gemini_api_key:
            # Initialize MessageBus for agent communication
            message_bus = MessageBus()
            print("  ✓ MessageBus initialized")
            
            llm_provider = LiteLLMProvider(
                api_key=gemini_api_key,
                default_model="gemini/gemini-2.0-flash"  # Use Gemini 2.0 Flash model
            )
            print("  ✓ Gemini LLM Provider initialized (model: gemini-2.0-flash)")
            
            # Initialize MultiTenantAgentLoop with all required parameters
            agent_loop = MultiTenantAgentLoop(
                bus=message_bus,
                provider=llm_provider,
                workspace_manager=workspace_manager,
                model="gemini/gemini-2.0-flash"
            )
            print("  ✓ MultiTenantAgentLoop initialized")
        else:
            print("  ⚠ No API key found, LLM Provider not initialized")
    except Exception as e:
        print(f"  ⚠ Failed to initialize LLM components: {e}")
        import traceback
        traceback.print_exc()
        agent_loop = None
        llm_provider = None
        message_bus = None
    
    # Initialize report generator and scheduler (optional, only if APScheduler is available)
    print("\n[4] Initializing Report Generator & Scheduler...")
    try:
        from nanobot.services.scheduler import ReportScheduler
        from nanobot.services.report_generator_simple import ReportGenerator
        
        # Initialize ReportGenerator with required dependencies
        report_generator = ReportGenerator(
            config_manager=config_manager,
            workspace_manager=workspace_manager,
            agent_loop=agent_loop,  # Now using real LLM if available
            max_retries=3
        )
        print("  ✓ Report Generator initialized")
        
        # Initialize ReportScheduler with the report_generator
        report_scheduler = ReportScheduler(
            workspace_base="~/.nanobot/workspaces",
            report_generator=report_generator
        )
        await report_scheduler.start()
        print("  ✓ Report Scheduler initialized and started")
    except ImportError as e:
        print(f"  ⚠ Report Scheduler not available: {e}")
        report_scheduler = None
        report_generator = None
    
    print("\n" + "=" * 60)
    print("nanobot Multi-Tenant Service Started!")
    print("=" * 60)
    
    yield
    
    # Cleanup
    print("\nShutting down...")
    if report_scheduler:
        await report_scheduler.stop()
    print("Goodbye!")


# Create FastAPI app
app = FastAPI(
    title="nanobot Multi-Tenant Service",
    description="AI-powered multi-tenant assistant service for C端 users",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helper functions

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract and validate user from JWT token."""
    # For demo purposes, just return the token as user_id
    # In production, implement proper JWT validation
    try:
        # This is a placeholder - implement proper JWT validation
        # For now, we simply return the credentials as the user_id
        # This allows testing without JWT library
        return credentials.credentials
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


# API Endpoints

@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "nanobot Multi-Tenant Service",
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_url": "/health"
    }


@app.get("/health", response_model=HealthCheck, tags=["health"])
async def health_check():
    """Health check endpoint."""
    global workspace_manager, config_manager, report_scheduler
    
    return HealthCheck(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        services={
            "workspace_manager": workspace_manager is not None,
            "config_manager": config_manager is not None,
            "report_scheduler": report_scheduler is not None and report_scheduler.scheduler.running if report_scheduler else False
        }
    )


# User Management Endpoints

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["users"])
async def create_user(user: UserCreate):
    """Create a new user with workspace."""
    global config_manager, workspace_manager
    
    if not config_manager or not workspace_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )
    
    # Check if user already exists
    existing_config = config_manager.get_config(user.user_id)
    if existing_config:
        # User already exists, return existing user info
        # Return 200 OK instead of 409 CONFLICT for idempotent behavior
        return UserResponse(**existing_config.to_dict())
    
    try:
        # Create workspace (idempotent - will not fail if already exists)
        try:
            workspace_manager.create_workspace(
                user_id=user.user_id,
                template_data=user.initial_data
            )
        except FileExistsError:
            # Workspace already exists, which is fine
            pass
        
        # Create user config - this will raise ValueError if user exists
        try:
            config = config_manager.create_user(user.user_id, user.initial_data)
            return UserResponse(**config.to_dict())
        except ValueError as ve:
            # User already exists - return the existing user
            if "already exists" in str(ve).lower():
                existing_config = config_manager.get_config(user.user_id)
                if existing_config:
                    return UserResponse(**existing_config.to_dict())
            # Re-raise other ValueErrors
            raise
        except Exception as e:
            # Check if it's a "user already exists" error
            if "already exists" in str(e).lower():
                existing_config = config_manager.get_config(user.user_id)
                if existing_config:
                    return UserResponse(**existing_config.to_dict())
            # Re-raise other exceptions
            raise
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@app.get("/users/{user_id}", response_model=UserResponse, tags=["users"])
async def get_user(user_id: str):
    """Get user information."""
    global config_manager
    
    if not config_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )
    
    config = config_manager.get_config(user_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    return UserResponse(**config.to_dict())


@app.put("/users/{user_id}/watchlist", response_model=UserResponse, tags=["users"])
async def update_watchlist(user_id: str, watchlist: WatchlistUpdate):
    """Update user's watchlist."""
    global config_manager
    
    if not config_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )
    
    # Convert to dict, excluding None values
    watchlist_data = watchlist.dict(exclude_unset=True)
    
    updated_config = config_manager.update_watchlist(user_id, watchlist_data)
    if not updated_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    return UserResponse(**updated_config.to_dict())


@app.put("/users/{user_id}/preferences", response_model=UserResponse, tags=["users"])
async def update_preferences(user_id: str, preferences: PreferencesUpdate):
    """Update user's preferences."""
    global config_manager
    
    if not config_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )
    
    # Convert to dict, excluding None values
    prefs_data = preferences.dict(exclude_unset=True)
    
    updated_config = config_manager.update_preferences(user_id, prefs_data)
    if not updated_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    return UserResponse(**updated_config.to_dict())


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["users"])
async def delete_user(user_id: str):
    """Delete a user and their workspace."""
    global config_manager, workspace_manager
    
    if not config_manager or not workspace_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )
    
    # Check if user exists
    if not config_manager.get_config(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    try:
        # Delete workspace
        workspace_manager.delete_workspace(user_id)
        
        # Delete config (actually just mark as deleted, real cleanup happens later)
        config_manager.delete_user(user_id)
        
        return None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )


@app.get("/users", response_model=List[Dict[str, Any]], tags=["users"])
async def list_users():
    """List all users."""
    global config_manager
    
    if not config_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not initialized"
        )
    
    users = config_manager.list_users()
    return [{"user_id": uid} for uid in users]


# Chat Endpoints

@app.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """Send a chat message to the AI assistant."""
    # This would use the MultiTenantAgentLoop
    # For now, return a placeholder
    return ChatResponse(
        response="This is a placeholder response. Implement actual chat processing using MultiTenantAgentLoop.",
        session_id=request.session_id or str(uuid.uuid4()),
        user_id=user_id,
        processing_time_ms=0
    )


# Report Endpoints

@app.post("/reports", response_model=ReportResponse, tags=["reports"])
async def generate_report(
    request: ReportRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """Request generation of a report."""
    global report_scheduler
    
    report_id = str(uuid.uuid4())
    
    # Check if report scheduler is available
    if not report_scheduler:
        return ReportResponse(
            report_id=report_id,
            user_id=user_id,
            status="error",
            message="Report scheduler is not available",
            estimated_completion_time=None
        )
    
    # Schedule report generation immediately using background task
    async def generate_report_task():
        """Background task to generate report."""
        try:
            logger.info(f"Starting immediate report generation for {user_id}")
            
            # Use the scheduler's generate_report_now method
            result_report_id = await report_scheduler.generate_report_now(
                user_id=user_id,
                report_type=request.report_type
            )
            
            if result_report_id:
                logger.info(f"Report generated successfully for {user_id}: {result_report_id}")
            else:
                logger.error(f"Failed to generate report for {user_id}")
                
        except Exception as e:
            logger.error(f"Error in report generation task for {user_id}: {e}")
    
    # Add the task to background tasks
    background_tasks.add_task(generate_report_task)
    
    return ReportResponse(
        report_id=report_id,
        user_id=user_id,
        status="scheduled",
        message=f"Report generation scheduled and will run immediately. Report ID: {report_id}",
        estimated_completion_time="1-2 minutes"
    )


@app.get("/reports/{report_id}", response_model=ReportStatus, tags=["reports"])
async def get_report_status(
    report_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get the status of a report."""
    # This would check the report status
    return ReportStatus(
        report_id=report_id,
        user_id=user_id,
        status="completed",
        progress=100,
        content="Report content would be here...",
        created_at=datetime.now().isoformat(),
        completed_at=datetime.now().isoformat()
    )


# Schedule Endpoints

@app.get("/schedule", response_model=ScheduleInfo, tags=["schedule"])
async def get_schedule(user_id: str = Depends(get_current_user)):
    """Get user's scheduled tasks information."""
    return ScheduleInfo(
        user_id=user_id,
        daily_report={
            "enabled": True,
            "schedule": "09:00",
            "timezone": "Asia/Shanghai"
        },
        weekly_report={
            "enabled": True,
            "schedule": "Monday 09:00",
            "timezone": "Asia/Shanghai"
        },
        next_scheduled_jobs=[]
    )


# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
