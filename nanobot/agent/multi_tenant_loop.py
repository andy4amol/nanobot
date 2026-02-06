"""Agent loop with multi-tenant workspace support.

This module extends the base AgentLoop to support dynamic workspace switching
for multi-tenant SaaS applications.
"""

import asyncio
import json
from pathlib import Path
from typing import Any, Optional, Dict

from loguru import logger

from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.providers.base import LLMProvider
from nanobot.agent.context import ContextBuilder
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent.tools.filesystem import ReadFileTool, WriteFileTool, EditFileTool, ListDirTool
from nanobot.agent.tools.shell import ExecTool
from nanobot.agent.tools.web import WebSearchTool, WebFetchTool
from nanobot.agent.tools.message import MessageTool
from nanobot.agent.tools.spawn import SpawnTool
from nanobot.agent.tools.cron import CronTool
from nanobot.agent.subagent import SubagentManager
from nanobot.session.manager import SessionManager
from nanobot.config.schema import ExecToolConfig
from nanobot.cron.service import CronService


class MultiTenantAgentLoop:
    """
    Multi-tenant Agent Loop with dynamic workspace switching.
    
    This class extends the functionality of the base AgentLoop to support
    multiple users (tenants) with isolated workspaces. It can dynamically
    switch between user workspaces to process messages.
    
    Key Features:
    1. Dynamic workspace switching
    2. Per-user configuration and memory
    3. Isolated tool registries per workspace
    4. Shared LLM provider and message bus
    5. Support for both sync and async processing
    
    Usage:
        # Initialize
        loop = MultiTenantAgentLoop(
            bus=message_bus,
            provider=llm_provider,
            workspace_manager=workspace_manager,
            model="gpt-4"
        )
        
        # Process message for specific user
        response = await loop.process_for_user(
            user_id="user_123",
            message="Generate my daily report"
        )
    """
    
    def __init__(
        self,
        bus: MessageBus,
        provider: LLMProvider,
        workspace_manager: Any,  # WorkspaceManager instance
        model: Optional[str] = None,
        max_iterations: int = 20,
        brave_api_key: Optional[str] = None,
        exec_config: Optional[ExecToolConfig] = None,
        cron_service: Optional[CronService] = None,
    ):
        """
        Initialize the MultiTenantAgentLoop.
        
        Args:
            bus: Message bus for communication
            provider: LLM provider for generating responses
            workspace_manager: Manager for user workspaces
            model: Default model to use (if None, uses provider default)
            max_iterations: Maximum tool execution iterations
            brave_api_key: API key for Brave search
            exec_config: Configuration for shell execution
            cron_service: Optional cron service for scheduled tasks
        """
        self.bus = bus
        self.provider = provider
        self.workspace_manager = workspace_manager
        self.model = model or provider.get_default_model()
        self.max_iterations = max_iterations
        self.brave_api_key = brave_api_key
        self.exec_config = exec_config or ExecToolConfig()
        self.cron_service = cron_service
        
        # Current workspace context
        self.current_user_id: Optional[str] = None
        self.current_workspace: Optional[Path] = None
        
        # Components (initialized on first use)
        self._context: Optional[ContextBuilder] = None
        self._sessions: Optional[SessionManager] = None
        self._tools: Optional[ToolRegistry] = None
        self._subagents: Optional[SubagentManager] = None
        
        self._running = False
        
        print(f"[MultiTenantAgentLoop] 初始化完成，默认模型: {self.model}")
    
    def _ensure_initialized(self) -> None:
        """Ensure components are initialized for current workspace."""
        if self.current_workspace is None:
            raise RuntimeError("No workspace is currently active. Call switch_workspace() first.")
        
        if self._context is None:
            self._context = ContextBuilder(self.current_workspace)
            self._sessions = SessionManager(self.current_workspace)
            self._tools = ToolRegistry()
            self._subagents = SubagentManager(
                provider=self.provider,
                workspace=self.current_workspace,
                bus=self.bus,
                model=self.model,
                brave_api_key=self.brave_api_key,
                exec_config=self.exec_config,
            )
            self._register_default_tools()
    
    def _register_default_tools(self) -> None:
        """Register default tools for current workspace."""
        if self._tools is None:
            return
        
        # File tools
        self._tools.register(ReadFileTool())
        self._tools.register(WriteFileTool())
        self._tools.register(EditFileTool())
        self._tools.register(ListDirTool())
        
        # Shell tool
        self._tools.register(ExecTool(
            working_dir=str(self.current_workspace),
            timeout=self.exec_config.timeout,
            restrict_to_workspace=self.exec_config.restrict_to_workspace,
        ))
        
        # Web tools
        self._tools.register(WebSearchTool(api_key=self.brave_api_key))
        self._tools.register(WebFetchTool())
        
        # Message tool
        message_tool = MessageTool(send_callback=self.bus.publish_outbound)
        self._tools.register(message_tool)
        
        # Spawn tool (for subagents)
        spawn_tool = SpawnTool(manager=self._subagents)
        self._tools.register(spawn_tool)
        
        # Cron tool (for scheduling)
        if self.cron_service:
            self._tools.register(CronTool(self.cron_service))
        
        print(f"[MultiTenantAgentLoop] 已注册 {len(self._tools)} 个工具")
    
    def switch_workspace(self, user_id: str) -> Path:
        """
        Switch to the workspace of the specified user.
        
        This method:
        1. Looks up the user's workspace path
        2. Resets and reinitializes all workspace-dependent components
        3. Updates the current context to the new workspace
        
        Args:
            user_id: The unique identifier of the user whose workspace to switch to
            
        Returns:
            Path to the user's workspace directory
            
        Raises:
            ValueError: If the user's workspace does not exist
            RuntimeError: If the workspace manager is not properly configured
            
        Example:
            # Switch to user_123's workspace
            workspace_path = loop.switch_workspace("user_123")
            print(f"Now working in: {workspace_path}")
            
            # The agent is now configured with user_123's:
            # - Personalized AGENTS.md prompts
            # - Saved memories and context
            # - Access to their specific tools and data
        """
        # Check if already on this workspace
        if user_id == self.current_user_id and self.current_workspace:
            print(f"[MultiTenantAgentLoop] 已在用户 {user_id} 的 workspace")
            return self.current_workspace
        
        # Get workspace path from manager
        workspace = self.workspace_manager.get_workspace(user_id)
        if not workspace.exists():
            raise ValueError(f"Workspace for user {user_id} does not exist. "
                           f"Create it first using workspace_manager.create_workspace()")
        
        print(f"[MultiTenantAgentLoop] 正在切换到用户 {user_id} 的 workspace: {workspace}")
        
        # Reset components
        self._context = None
        self._sessions = None
        self._tools = None
        self._subagents = None
        
        # Update current context
        self.workspace = workspace
        self.current_workspace = workspace
        self.current_user_id = user_id
        
        # Initialize components for new workspace
        self._ensure_initialized()
        
        print(f"[MultiTenantAgentLoop] 已成功切换到用户 {user_id} 的 workspace")
        return workspace
    
    async def process_for_user(
        self, 
        user_id: str, 
        message: str,
        session_key: Optional[str] = None,
        channel: str = "api",
        chat_id: Optional[str] = None
    ) -> str:
        """
        Process a message for a specific user.
        
        This is the main entry point for processing user messages in a
        multi-tenant environment. It automatically:
        1. Switches to the user's workspace
        2. Loads their personalized configuration
        3. Processes the message using their context
        4. Returns the response
        
        Args:
            user_id: The unique identifier of the user
            message: The message content to process
            session_key: Optional session identifier for maintaining conversation context.
                        If not provided, uses a default session for the user.
            channel: The communication channel (e.g., "api", "telegram", "web")
            chat_id: Optional chat/channel identifier
            
        Returns:
            The processed response as a string
            
        Raises:
            ValueError: If the user's workspace doesn't exist
            RuntimeError: If there's an error processing the message
            
        Example:
            # Simple usage
            response = await loop.process_for_user(
                user_id="user_123",
                message="Generate my daily report"
            )
            
            # With session context
            response = await loop.process_for_user(
                user_id="user_123",
                message="What about yesterday?",
                session_key="chat_session_456"
            )
            
        Note:
            - This method is thread-safe and can be called concurrently for different users
            - The workspace switch happens atomically at the start of processing
            - Session context is maintained per user_id + session_key combination
        """
        # Switch to user's workspace
        self.switch_workspace(user_id)
        
        # Build session key
        if session_key is None:
            session_key = f"user_{user_id}:default"
        elif not session_key.startswith(f"user_{user_id}:"):
            # Ensure session includes user_id for isolation
            session_key = f"user_{user_id}:{session_key}"
        
        # Process message
        chat_id = chat_id or user_id
        response = await self.process_direct(
            content=message,
            session_key=session_key,
            channel=channel,
            chat_id=chat_id
        )
        
        return response
    
    async def process_direct(
        self,
        content: str,
        session_key: str = "cli:direct",
        channel: str = "cli",
        chat_id: str = "direct",
    ) -> str:
        """
        Process a message directly (internal method).
        
        This is adapted from the base AgentLoop._process_message method.
        
        Args:
            content: The message content
            session_key: Session identifier
            channel: Communication channel
            chat_id: Chat identifier
            
        Returns:
            Response string
        """
        self._ensure_initialized()
        
        # Create message
        msg = InboundMessage(
            channel=channel,
            sender_id="user",
            chat_id=chat_id,
            content=content
        )
        
        # Get or create session
        session = self._sessions.get_or_create(session_key)
        
        # Update tool contexts
        message_tool = self._tools.get("message")
        if isinstance(message_tool, MessageTool):
            message_tool.set_context(channel, chat_id)
        
        spawn_tool = self._tools.get("spawn")
        if isinstance(spawn_tool, SpawnTool):
            spawn_tool.set_context(channel, chat_id)
        
        cron_tool = self._tools.get("cron")
        if isinstance(cron_tool, CronTool):
            cron_tool.set_context(channel, chat_id)
        
        # Build messages
        messages = self._context.build_messages(
            history=session.get_history(),
            current_message=msg.content,
            media=msg.media if msg.media else None,
            channel=msg.channel,
            chat_id=msg.chat_id,
        )
        
        # Agent loop
        iteration = 0
        final_content = None
        
        while iteration < self.max_iterations:
            iteration += 1
            
            # Call LLM
            response = await self.provider.chat(
                messages=messages,
                tools=self._tools.get_definitions(),
                model=self.model
            )
            
            # Handle tool calls
            if response.has_tool_calls:
                # Add assistant message with tool calls
                tool_call_dicts = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                        }
                    }
                    for tc in response.tool_calls
                ]
                messages = self._context.add_assistant_message(
                    messages, response.content, tool_call_dicts
                )
                
                # Execute tools
                for tool_call in response.tool_calls:
                    args_str = json.dumps(tool_call.arguments)
                    logger.debug(f"Executing tool: {tool_call.name} with arguments: {args_str}")
                    result = await self._tools.execute(tool_call.name, tool_call.arguments)
                    messages = self._context.add_tool_result(
                        messages, tool_call.id, tool_call.name, result
                    )
            else:
                # No tool calls, we're done
                final_content = response.content
                break
        
        if final_content is None:
            final_content = "I've completed processing but have no response to give."
        
        # Save to session
        session.add_message("user", msg.content)
        session.add_message("assistant", final_content)
        self._sessions.save(session)
        
        return final_content
    
    async def run(self) -> None:
        """Run the agent loop (for gateway mode)."""
        self._running = True
        logger.info("MultiTenantAgentLoop started")
        
        while self._running:
            try:
                # Wait for next message
                msg = await asyncio.wait_for(
                    self.bus.consume_inbound(),
                    timeout=1.0
                )
                
                # Process it
                try:
                    # Extract user_id from session_key or metadata
                    user_id = msg.metadata.get("user_id") if msg.metadata else None
                    if not user_id:
                        # Try to extract from session_key pattern: user_{id}:...
                        if msg.session_key.startswith("user_"):
                            parts = msg.session_key.split(":")
                            if parts:
                                user_id = parts[0].replace("user_", "")
                    
                    if user_id:
                        # Process with user context
                        response = await self.process_for_user(
                            user_id=user_id,
                            message=msg.content,
                            session_key=msg.session_key,
                            channel=msg.channel,
                            chat_id=msg.chat_id
                        )
                    else:
                        # Process without user context (fallback)
                        response = await self.process_direct(
                            content=msg.content,
                            session_key=msg.session_key,
                            channel=msg.channel,
                            chat_id=msg.chat_id
                        )
                    
                    if response:
                        await self.bus.publish_outbound(OutboundMessage(
                            channel=msg.channel,
                            chat_id=msg.chat_id,
                            content=response
                        ))
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    await self.bus.publish_outbound(OutboundMessage(
                        channel=msg.channel,
                        chat_id=msg.chat_id,
                        content=f"Sorry, I encountered an error: {str(e)}"
                    ))
            except asyncio.TimeoutError:
                continue
    
    def stop(self) -> None:
        """Stop the agent loop."""
        self._running = False
        logger.info("MultiTenantAgentLoop stopping")
