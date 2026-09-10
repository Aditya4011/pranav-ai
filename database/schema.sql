-- Saarthi Finance / SIH prototype schema
-- PostgreSQL 15+ with PostGIS. Replace simulated data with verified official datasets.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE application_status AS ENUM ('draft','eligibility_checked','partner_selected','documents_pending','under_review','approved','rejected','withdrawn');
CREATE TYPE eligibility_state AS ENUM ('eligible','possibly_eligible','not_eligible');

CREATE TABLE users (
  user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(120) NOT NULL,
  age SMALLINT CHECK (age BETWEEN 18 AND 100),
  income NUMERIC(14,2) CHECK (income >= 0),
  project_type VARCHAR(80),
  project_cost NUMERIC(14,2) CHECK (project_cost >= 0),
  education_status VARCHAR(80),
  state VARCHAR(80), district VARCHAR(80), pincode CHAR(6),
  preferred_language VARCHAR(12) DEFAULT 'en',
  location GEOGRAPHY(POINT,4326),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE schemes (
  scheme_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scheme_code VARCHAR(80) UNIQUE NOT NULL,
  scheme_name VARCHAR(220) NOT NULL,
  scheme_type VARCHAR(80) NOT NULL,
  maximum_loan NUMERIC(14,2) NOT NULL,
  interest_rate NUMERIC(6,3) NOT NULL,
  income_limit NUMERIC(14,2),
  moratorium_months SMALLINT DEFAULT 0,
  tenure_months SMALLINT,
  eligible_purpose JSONB NOT NULL DEFAULT '[]',
  eligibility_rules JSONB NOT NULL DEFAULT '{}',
  required_documents JSONB NOT NULL DEFAULT '[]',
  source_url TEXT,
  source_verified_at TIMESTAMPTZ,
  is_prototype_data BOOLEAN NOT NULL DEFAULT TRUE,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE channel_partners (
  partner_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  partner_name VARCHAR(220) NOT NULL,
  partner_type VARCHAR(80) NOT NULL,
  latitude DOUBLE PRECISION NOT NULL,
  longitude DOUBLE PRECISION NOT NULL,
  location GEOGRAPHY(POINT,4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(longitude, latitude),4326)::geography) STORED,
  address TEXT NOT NULL,
  phone VARCHAR(40),
  supported_schemes JSONB NOT NULL DEFAULT '[]',
  eligibility_status VARCHAR(50) NOT NULL,
  fund_status VARCHAR(50) NOT NULL,
  npa_overdue_status VARCHAR(80) NOT NULL,
  operational BOOLEAN NOT NULL DEFAULT TRUE,
  status_verified_at TIMESTAMPTZ,
  is_prototype_data BOOLEAN NOT NULL DEFAULT TRUE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX channel_partners_location_gix ON channel_partners USING GIST(location);

CREATE TABLE eligibility_checks (
  check_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  scheme_id UUID NOT NULL REFERENCES schemes(scheme_id),
  status eligibility_state NOT NULL,
  match_score NUMERIC(5,2) CHECK (match_score BETWEEN 0 AND 100),
  reasons JSONB NOT NULL DEFAULT '[]',
  rule_snapshot JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE applications (
  application_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(user_id),
  scheme_id UUID NOT NULL REFERENCES schemes(scheme_id),
  partner_id UUID REFERENCES channel_partners(partner_id),
  application_status application_status NOT NULL DEFAULT 'draft',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX applications_user_idx ON applications(user_id, created_at DESC);
CREATE INDEX applications_scheme_idx ON applications(scheme_id, application_status);
CREATE INDEX applications_partner_idx ON applications(partner_id, application_status);

CREATE TABLE audit_log (
  audit_id BIGSERIAL PRIMARY KEY,
  actor_user_id UUID,
  actor_role VARCHAR(50) NOT NULL,
  action VARCHAR(120) NOT NULL,
  entity_type VARCHAR(80),
  entity_id VARCHAR(120),
  metadata JSONB NOT NULL DEFAULT '{}',
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Never store secrets, Aadhaar, PAN, bank credentials, or full KYC documents here by default.
-- If a production workflow requires regulated identifiers, isolate them in a purpose-specific,
-- encrypted vault with strict retention, access logging, legal basis, and consent controls.
