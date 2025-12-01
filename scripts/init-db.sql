-- ============================================
-- IPA Platform Database Initialization Script
-- ============================================
-- This script is automatically executed when PostgreSQL container starts
-- Sprint 0: Infrastructure Foundation
--
-- Tables:
--   - users: User accounts
--   - agents: AI Agent definitions
--   - workflows: Workflow definitions
--   - executions: Workflow execution instances
--   - checkpoints: Human-in-the-loop checkpoints
--   - audit_logs: Audit trail

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- For similarity search (Few-shot learning)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- For encryption functions

-- ============================================
-- Users Table
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'user',  -- admin, operator, user, viewer
    is_active BOOLEAN DEFAULT true,
    azure_ad_object_id VARCHAR(255) UNIQUE,    -- For Azure AD integration
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- ============================================
-- Agents Table
-- ============================================
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),              -- it_triage, customer_service, escalation, etc.
    code TEXT,                          -- Python code for Agent Framework
    config JSONB DEFAULT '{}',          -- Agent configuration
    tools JSONB DEFAULT '[]',           -- Tool definitions
    status VARCHAR(50) DEFAULT 'draft', -- draft, active, deprecated
    version INTEGER DEFAULT 1,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agents_category ON agents(category);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);

-- ============================================
-- Workflows Table
-- ============================================
CREATE TABLE IF NOT EXISTS workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    trigger_type VARCHAR(50),           -- manual, webhook, schedule, event
    trigger_config JSONB DEFAULT '{}',  -- Trigger configuration
    graph_definition JSONB NOT NULL,    -- Workflow graph (nodes, edges)
    status VARCHAR(50) DEFAULT 'draft', -- draft, active, paused, deprecated
    version INTEGER DEFAULT 1,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status);
CREATE INDEX IF NOT EXISTS idx_workflows_trigger_type ON workflows(trigger_type);

-- ============================================
-- Executions Table
-- ============================================
CREATE TABLE IF NOT EXISTS executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID REFERENCES workflows(id) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, running, waiting_approval, completed, failed, cancelled
    input_data JSONB DEFAULT '{}',
    output_data JSONB,
    error TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    -- LLM usage tracking
    llm_calls INTEGER DEFAULT 0,
    llm_tokens INTEGER DEFAULT 0,
    llm_cost DECIMAL(10, 4) DEFAULT 0,
    -- Agent Framework state
    state_snapshot JSONB,               -- For checkpoint/resume
    current_step VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_executions_workflow_id ON executions(workflow_id);
CREATE INDEX IF NOT EXISTS idx_executions_status ON executions(status);
CREATE INDEX IF NOT EXISTS idx_executions_created_at ON executions(created_at);

-- ============================================
-- Checkpoints Table (Human-in-the-loop)
-- ============================================
CREATE TABLE IF NOT EXISTS checkpoints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id UUID REFERENCES executions(id) NOT NULL,
    step VARCHAR(255) NOT NULL,
    checkpoint_type VARCHAR(50) NOT NULL,  -- approval, review, input, confirmation
    state JSONB NOT NULL,                  -- Checkpoint state data
    request_data JSONB,                    -- Data presented to human
    response_data JSONB,                   -- Human response
    status VARCHAR(50) DEFAULT 'pending',  -- pending, approved, rejected, timeout
    assigned_to UUID REFERENCES users(id),
    approved_by UUID REFERENCES users(id),
    feedback TEXT,
    timeout_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_execution_id ON checkpoints(execution_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_status ON checkpoints(status);
CREATE INDEX IF NOT EXISTS idx_checkpoints_assigned_to ON checkpoints(assigned_to);

-- ============================================
-- Audit Logs Table (Append-only)
-- ============================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id UUID REFERENCES executions(id),
    action VARCHAR(255) NOT NULL,          -- workflow_started, agent_executed, checkpoint_created, etc.
    actor VARCHAR(255),                    -- User or Agent identifier
    actor_type VARCHAR(50),                -- user, agent, system
    resource_type VARCHAR(100),            -- workflow, agent, checkpoint, etc.
    resource_id UUID,
    details JSONB DEFAULT '{}',            -- Action-specific details
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_execution_id ON audit_logs(execution_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

-- ============================================
-- Agent Templates Table (Sprint 4)
-- ============================================
CREATE TABLE IF NOT EXISTS agent_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100) NOT NULL,
    template_code TEXT NOT NULL,
    parameters JSONB DEFAULT '[]',         -- Template parameters
    default_config JSONB DEFAULT '{}',
    tags VARCHAR(255)[],
    version VARCHAR(50) DEFAULT '1.0.0',
    is_builtin BOOLEAN DEFAULT false,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agent_templates_category ON agent_templates(category);

-- ============================================
-- Learning Cases Table (Sprint 4 - Few-shot)
-- ============================================
CREATE TABLE IF NOT EXISTS learning_cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id UUID REFERENCES executions(id),
    scenario VARCHAR(255) NOT NULL,
    original_input TEXT NOT NULL,
    original_output TEXT NOT NULL,
    corrected_output TEXT,
    feedback TEXT,
    is_approved BOOLEAN DEFAULT false,
    approved_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_learning_cases_scenario ON learning_cases(scenario);
CREATE INDEX IF NOT EXISTS idx_learning_cases_approved ON learning_cases(is_approved);
-- Trigram index for similarity search
CREATE INDEX IF NOT EXISTS idx_learning_cases_input_trgm ON learning_cases USING gin(original_input gin_trgm_ops);

-- ============================================
-- Trigger Function: Auto-update updated_at
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_workflows_updated_at BEFORE UPDATE ON workflows FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_checkpoints_updated_at BEFORE UPDATE ON checkpoints FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_agent_templates_updated_at BEFORE UPDATE ON agent_templates FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Initial Data: Default Admin User
-- ============================================
INSERT INTO users (email, name, role, password_hash)
VALUES ('admin@ipa-platform.local', 'System Admin', 'admin', 'CHANGE_THIS_PASSWORD_HASH')
ON CONFLICT (email) DO NOTHING;

-- ============================================
-- Completion Log
-- ============================================
DO $$
BEGIN
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'IPA Platform database initialized';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  - users';
    RAISE NOTICE '  - agents';
    RAISE NOTICE '  - workflows';
    RAISE NOTICE '  - executions';
    RAISE NOTICE '  - checkpoints';
    RAISE NOTICE '  - audit_logs';
    RAISE NOTICE '  - agent_templates';
    RAISE NOTICE '  - learning_cases';
    RAISE NOTICE '==========================================';
END $$;
