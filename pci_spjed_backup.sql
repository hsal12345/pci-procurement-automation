--
-- PostgreSQL database dump
--

\restrict oIhOd1p6kumzQFgFaqwZHb5IqnbMqrjlrKgrAavomUENwU03jrnJKhr8lZWsZLH

-- Dumped from database version 16.15
-- Dumped by pg_dump version 16.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ai_usage_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ai_usage_logs (
    provider character varying(50) NOT NULL,
    model character varying(100) NOT NULL,
    task_type character varying(50) NOT NULL,
    prompt_tokens integer NOT NULL,
    completion_tokens integer NOT NULL,
    total_tokens integer NOT NULL,
    estimated_cost_usd numeric(10,6) NOT NULL,
    status character varying(32) NOT NULL,
    error_message text,
    latency_ms integer NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.ai_usage_logs OWNER TO postgres;

--
-- Name: approvals; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.approvals (
    revision_id uuid NOT NULL,
    approver_name character varying(255) NOT NULL,
    approver_role character varying(64) NOT NULL,
    decision character varying(32) NOT NULL,
    decision_reason text,
    reviewed_manifest_hash character varying(64),
    signed_at timestamp with time zone NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.approvals OWNER TO postgres;

--
-- Name: archive_records; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.archive_records (
    package_id uuid NOT NULL,
    revision_id uuid NOT NULL,
    target_provider character varying(32) NOT NULL,
    folder_path character varying(512) NOT NULL,
    drive_folder_id character varying(128),
    status character varying(32) NOT NULL,
    attempt_count integer NOT NULL,
    last_error text,
    last_attempt_at timestamp with time zone,
    synced_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.archive_records OWNER TO postgres;

--
-- Name: artifacts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.artifacts (
    job_id uuid,
    revision_id uuid NOT NULL,
    doc_code character varying(32),
    format character varying(16) NOT NULL,
    filename character varying(255) NOT NULL,
    file_path character varying(512) NOT NULL,
    file_size integer NOT NULL,
    sha256_hash character varying(64) NOT NULL,
    is_draft boolean NOT NULL,
    archive_status character varying(32) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.artifacts OWNER TO postgres;

--
-- Name: audit_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.audit_events (
    entity_name character varying(64) NOT NULL,
    entity_id character varying(64) NOT NULL,
    action character varying(32) NOT NULL,
    actor character varying(100) NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    before_state json,
    after_state json,
    ip_address character varying(64),
    reason text,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.audit_events OWNER TO postgres;

--
-- Name: budget_classifications; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.budget_classifications (
    fiscal_year integer NOT NULL,
    activity_code character varying(64),
    activity_name character varying(255) NOT NULL,
    sub_activity character varying(255),
    account_code character varying(64),
    account_name character varying(255) NOT NULL,
    funding_source_code character varying(32),
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.budget_classifications OWNER TO postgres;

--
-- Name: companies; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.companies (
    legal_name character varying(255) NOT NULL,
    npwp character varying(32),
    address text NOT NULL,
    subdistrict character varying(100),
    city character varying(100) NOT NULL,
    postal_code character varying(16),
    email character varying(128),
    phone character varying(32),
    bank_name character varying(100),
    bank_account_number character varying(64),
    bank_account_holder character varying(255),
    director_name character varying(255) NOT NULL,
    director_title character varying(100) NOT NULL,
    director_sk_number character varying(128),
    logo_path character varying(255),
    is_active boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.companies OWNER TO postgres;

--
-- Name: company_officials; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.company_officials (
    company_id uuid NOT NULL,
    person_name character varying(255) NOT NULL,
    role character varying(64) NOT NULL,
    role_title character varying(100) NOT NULL,
    nip character varying(32),
    position_sk_number character varying(128),
    is_active boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.company_officials OWNER TO postgres;

--
-- Name: document_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.document_events (
    revision_id uuid NOT NULL,
    event_code character varying(32) NOT NULL,
    event_date date NOT NULL,
    day_name_id character varying(32),
    location character varying(100) NOT NULL,
    notes text,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.document_events OWNER TO postgres;

--
-- Name: document_numbers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.document_numbers (
    revision_id uuid NOT NULL,
    doc_code character varying(32) NOT NULL,
    doc_number character varying(128) NOT NULL,
    issuer character varying(32) NOT NULL,
    counter_val integer,
    issue_date date,
    is_reserved boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.document_numbers OWNER TO postgres;

--
-- Name: findings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.findings (
    run_id uuid NOT NULL,
    rule_code character varying(32) NOT NULL,
    severity character varying(16) NOT NULL,
    doc_code character varying(32),
    sheet_name character varying(64),
    cell_range character varying(32),
    field_name character varying(100),
    original_value text,
    proposed_value text,
    message text NOT NULL,
    disposition character varying(32) NOT NULL,
    disposition_reason text,
    disposition_actor character varying(100),
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.findings OWNER TO postgres;

--
-- Name: funding_sources; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.funding_sources (
    code character varying(32) NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    is_active boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.funding_sources OWNER TO postgres;

--
-- Name: generation_jobs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.generation_jobs (
    revision_id uuid NOT NULL,
    status character varying(32) NOT NULL,
    progress_percent integer NOT NULL,
    error_message text,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.generation_jobs OWNER TO postgres;

--
-- Name: imports; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.imports (
    original_filename character varying(255) NOT NULL,
    file_hash character varying(64) NOT NULL,
    file_size integer NOT NULL,
    uploaded_at timestamp with time zone NOT NULL,
    uploader character varying(100) NOT NULL,
    status character varying(32) NOT NULL,
    candidate_payload json,
    sheet_metadata json,
    detected_discrepancies json,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.imports OWNER TO postgres;

--
-- Name: items; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.items (
    sku character varying(64),
    canonical_description character varying(255) NOT NULL,
    default_spec text,
    brand character varying(100),
    category character varying(100),
    default_unit character varying(32),
    is_active boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.items OWNER TO postgres;

--
-- Name: logistics_evidence; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.logistics_evidence (
    revision_id uuid NOT NULL,
    file_path character varying(512) NOT NULL,
    original_filename character varying(255) NOT NULL,
    file_size integer NOT NULL,
    mime_type character varying(64) NOT NULL,
    sha256_hash character varying(64) NOT NULL,
    evidence_type character varying(64) NOT NULL,
    description text,
    uploaded_by character varying(100) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.logistics_evidence OWNER TO postgres;

--
-- Name: logistics_records; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.logistics_records (
    revision_id uuid NOT NULL,
    dispatch_date date,
    receipt_date date,
    delivery_reference character varying(128),
    courier_name character varying(128),
    vehicle_plate character varying(32),
    inspection_status character varying(32) NOT NULL,
    inspection_notes text,
    inspected_by character varying(128),
    inspected_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.logistics_records OWNER TO postgres;

--
-- Name: number_counters; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.number_counters (
    scope_key character varying(64) NOT NULL,
    counter_val integer NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.number_counters OWNER TO postgres;

--
-- Name: numbering_policies; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.numbering_policies (
    doc_code character varying(32) NOT NULL,
    issuer character varying(32) NOT NULL,
    pattern character varying(128) NOT NULL,
    reset_period character varying(32) NOT NULL,
    is_active boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.numbering_policies OWNER TO postgres;

--
-- Name: official_appointments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.official_appointments (
    school_id uuid NOT NULL,
    person_name character varying(255) NOT NULL,
    nip character varying(32),
    role character varying(64) NOT NULL,
    position_sk_number character varying(128),
    valid_from date NOT NULL,
    valid_to date,
    is_active boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.official_appointments OWNER TO postgres;

--
-- Name: package_profiles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.package_profiles (
    code character varying(64) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    required_doc_codes json NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.package_profiles OWNER TO postgres;

--
-- Name: package_revisions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.package_revisions (
    package_id uuid NOT NULL,
    revision_number integer NOT NULL,
    version integer NOT NULL,
    status character varying(32) NOT NULL,
    ai_review_status character varying(32) NOT NULL,
    school_snapshot json NOT NULL,
    company_snapshot json NOT NULL,
    tax_policy_snapshot json NOT NULL,
    officials_snapshot json NOT NULL,
    subtotal numeric(20,4) NOT NULL,
    tax_total numeric(20,4) NOT NULL,
    grand_total numeric(20,4) NOT NULL,
    terbilang_grand_total text,
    is_locked boolean NOT NULL,
    notes text,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.package_revisions OWNER TO postgres;

--
-- Name: packages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.packages (
    package_number character varying(64) NOT NULL,
    school_id uuid NOT NULL,
    fiscal_year integer NOT NULL,
    quarter integer NOT NULL,
    funding_source_id uuid,
    budget_id uuid,
    current_revision_id uuid,
    status character varying(32) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.packages OWNER TO postgres;

--
-- Name: revision_lines; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.revision_lines (
    revision_id uuid NOT NULL,
    line_number integer NOT NULL,
    item_id uuid,
    original_description text NOT NULL,
    confirmed_description text NOT NULL,
    specification text,
    quantity numeric(18,4) NOT NULL,
    received_quantity numeric(18,4),
    unit character varying(32) NOT NULL,
    hps_unit_price numeric(20,4) NOT NULL,
    offer_unit_price numeric(20,4) NOT NULL,
    final_unit_price numeric(20,4) NOT NULL,
    discount numeric(20,4) NOT NULL,
    line_total numeric(20,4) NOT NULL,
    condition character varying(32) NOT NULL,
    notes text,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.revision_lines OWNER TO postgres;

--
-- Name: schools; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.schools (
    name character varying(255) NOT NULL,
    npsn character varying(16),
    level character varying(16) NOT NULL,
    address text NOT NULL,
    subdistrict character varying(100),
    postal_code character varying(16),
    email character varying(128),
    phone character varying(32),
    letterhead_path character varying(255),
    is_active boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.schools OWNER TO postgres;

--
-- Name: tax_policy_versions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tax_policy_versions (
    policy_id character varying(64) NOT NULL,
    version integer NOT NULL,
    tax_type character varying(32) NOT NULL,
    rate numeric(12,8) NOT NULL,
    is_inclusive boolean NOT NULL,
    withholding_rule character varying(64) NOT NULL,
    rounding_rule character varying(32) NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    is_active boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.tax_policy_versions OWNER TO postgres;

--
-- Name: units; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.units (
    code character varying(32) NOT NULL,
    display_label character varying(64) NOT NULL,
    allowed_fractional boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.units OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    username character varying(64) NOT NULL,
    email character varying(128) NOT NULL,
    full_name character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    role character varying(64) NOT NULL,
    is_active boolean NOT NULL,
    last_login_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: validation_runs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.validation_runs (
    revision_id uuid NOT NULL,
    triggered_by character varying(100),
    run_at timestamp with time zone NOT NULL,
    passed boolean NOT NULL,
    error_count integer NOT NULL,
    warning_count integer NOT NULL,
    info_count integer NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


ALTER TABLE public.validation_runs OWNER TO postgres;

--
-- Data for Name: ai_usage_logs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.ai_usage_logs (provider, model, task_type, prompt_tokens, completion_tokens, total_tokens, estimated_cost_usd, status, error_message, latency_ms, id, created_at, updated_at) FROM stdin;
mock	mock-rule-engine	DISCREPANCY_AUDITOR	120	85	205	0.000000	SUCCESS	\N	15	d0f60295-6a97-4d3d-9c0a-f94ae74fceb3	2026-11-04 14:46:35.458022+00	2026-11-04 14:46:35.458036+00
mock	mock-rule-engine	PLAYGROUND	120	85	205	0.000000	SUCCESS	\N	15	b9c34166-bcba-4877-942c-276654eccd7a	2026-11-04 14:46:35.584932+00	2026-11-04 14:46:35.584937+00
mock	mock-rule-engine	PLAYGROUND	120	85	205	0.000000	SUCCESS	\N	15	f6a25011-1c6c-409b-812b-2ece300fa165	2026-11-04 14:46:35.597526+00	2026-11-04 14:46:35.597531+00
mock	mock-rule-engine	SYSTEM_KNOWLEDGE_CHAT	120	85	205	0.000000	SUCCESS	\N	15	149e02b9-bc0b-4e2f-bc5b-3d14b18e2edf	2026-11-04 16:15:18.658157+00	2026-11-04 16:15:18.658164+00
mock	mock-rule-engine	SYSTEM_KNOWLEDGE_CHAT	120	85	205	0.000000	SUCCESS	\N	15	3b1f6d4f-f15d-4d7d-b6f4-b78554041b5d	2026-11-04 16:15:31.941032+00	2026-11-04 16:15:31.941037+00
mock	mock-rule-engine	SYSTEM_KNOWLEDGE_CHAT	120	85	205	0.000000	SUCCESS	\N	15	6610317c-d925-4c5c-9175-5ef99b38d0df	2026-11-04 16:15:50.377366+00	2026-11-04 16:15:50.377372+00
custom	google/gemma-4-e4b	SYSTEM_KNOWLEDGE_CHAT	7133	1135	8268	0.000000	SUCCESS	\N	18647	d94bbfa3-ab39-41e8-b5dd-ebd8c122f56b	2026-11-04 16:17:06.208016+00	2026-11-04 16:17:06.208026+00
custom	google/gemma-4-e4b	SYSTEM_KNOWLEDGE_CHAT	0	0	0	0.000000	FAILED	Invalid \\escape: line 2 column 2025 (char 2026)	0	37bcc1e0-221d-42a6-9704-486cc03d2062	2026-11-04 16:18:49.544068+00	2026-11-04 16:18:49.544077+00
mock	mock-rule-engine	SYSTEM_KNOWLEDGE_CHAT	120	85	205	0.000000	FALLBACK	Fallback otomatis ke mesin aturan lokal akibat kegagalan provider (Invalid \\escape: line 2 column 2025 (char 2026)).	15	fffcb0f2-7243-4e0a-8a0d-5cd169c747ee	2026-11-04 16:18:49.555871+00	2026-11-04 16:18:49.555876+00
custom	google/gemma-4-e4b	SYSTEM_KNOWLEDGE_CHAT	7868	572	8440	0.000000	SUCCESS	\N	8904	e8379cb3-780c-4b95-82d1-08f702b96382	2026-11-04 16:26:00.812911+00	2026-11-04 16:26:00.812924+00
custom	google/gemma-4-e4b	SYSTEM_KNOWLEDGE_CHAT	7940	835	8775	0.000000	SUCCESS	\N	12628	9bc18a0e-c842-4fbb-a2d9-0469bc17a422	2026-11-04 16:26:40.671995+00	2026-11-04 16:26:40.672001+00
custom	google/gemma-4-e4b	DISCREPANCY_AUDITOR	1034	658	1692	0.000000	SUCCESS	\N	9258	4d34d32d-6fbe-4107-80c3-073db1714672	2026-11-04 16:38:04.033244+00	2026-11-04 16:38:04.033249+00
\.


--
-- Data for Name: approvals; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.approvals (revision_id, approver_name, approver_role, decision, decision_reason, reviewed_manifest_hash, signed_at, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: archive_records; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.archive_records (package_id, revision_id, target_provider, folder_path, drive_folder_id, status, attempt_count, last_error, last_attempt_at, synced_at, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: artifacts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.artifacts (job_id, revision_id, doc_code, format, filename, file_path, file_size, sha256_hash, is_draft, archive_status, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: audit_events; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.audit_events (entity_name, entity_id, action, actor, "timestamp", before_state, after_state, ip_address, reason, id, created_at, updated_at) FROM stdin;
PackageRevision	29d0bea0-adea-4845-8049-e9d826515973	AI_SEMANTIC_AUDIT	Staf Administrasi	2026-11-04 14:46:35.475758+00	{"ai_review_status": "NOT_RUN"}	{"ai_review_status": "COMPLETED", "findings_count": 1}	\N	Pemeriksaan semantik selesai: ditemukan 1 potensi substitusi merek.	801f63dd-1920-471e-a775-c7c7469eba8a	2026-11-04 14:46:35.476587+00	2026-11-04 14:46:35.476595+00
User	6eba36a5-0c2e-4ab9-96b9-aec8e917ab4e	LOGIN	Administrator Sistem	2026-11-04 16:12:52.922772+00	null	{"username": "sysadmin", "role": "SYSTEM_ADMINISTRATOR"}	\N	Pengguna berhasil masuk ke sistem	a3bfc378-29b1-4678-b902-903be4e1d965	2026-11-04 16:12:52.926287+00	2026-11-04 16:12:52.926292+00
PackageRevision	29d0bea0-adea-4845-8049-e9d826515973	AI_SEMANTIC_AUDIT	Administrator Sistem	2026-11-04 16:38:04.058045+00	{"ai_review_status": "NOT_RUN"}	{"ai_review_status": "COMPLETED", "findings_count": 1}	\N	Ditemukan potensi substitusi merek pada item pembersih porselen. Dokumen A menggunakan deskripsi generik, sementara Dokumen B mencantumkan nama merek spesifik ('Porstex'). Meskipun spesifikasi volume (1 Liter) konsisten, perubahan dari deskripsi umum ke merek dagang memerlukan klarifikasi untuk memastikan kesesuaian pengadaan.	a9813bfe-933e-4b5b-9c03-17216c01536f	2026-11-04 16:38:04.06039+00	2026-11-04 16:38:04.060395+00
User	6eba36a5-0c2e-4ab9-96b9-aec8e917ab4e	LOGIN	Administrator Sistem	2026-11-04 16:39:19.009713+00	null	{"username": "sysadmin", "role": "SYSTEM_ADMINISTRATOR"}	\N	Pengguna berhasil masuk ke sistem	92d119a8-9a57-4474-bb9d-14e373bcff47	2026-11-04 16:39:19.010216+00	2026-11-04 16:39:19.01022+00
\.


--
-- Data for Name: budget_classifications; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.budget_classifications (fiscal_year, activity_code, activity_name, sub_activity, account_code, account_name, funding_source_code, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: companies; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.companies (legal_name, npwp, address, subdistrict, city, postal_code, email, phone, bank_name, bank_account_number, bank_account_holder, director_name, director_title, director_sk_number, logo_path, is_active, id, created_at, updated_at) FROM stdin;
CV. PUSTAKA CEMERLANG INDONESIA	\N	Wisma Mitra Sunter Unit 3-03, Jakarta Utara	\N	Jakarta	\N	\N	\N	\N	\N	\N	Bambang Solifian	Direktur Utama	Akta Notaris No. 12 Th 2020	/storage/uploads/letterheads/companies/kop_rekanan.png	t	171aeb4a-3fba-42c8-ba1a-f11989994835	2026-11-04 14:46:35.41463+00	2026-11-04 15:34:19.131496+00
PT. SARANA EDUKASI NUSANTARA	02.987.654.3-021.000	Komp. Perkantoran Graha Niaga Lt. 3 No. 15	\N	Jakarta Pusat	\N	\N	\N	Bank Mandiri	1200098765432	PT Sarana Edukasi Nusantara	Ir. H. Gunawan Wibisono	Direktur Utama	Akta Notaris No. 88 Th 2021	\N	t	c7f238aa-49a6-4909-8a5d-a882f2461b09	2026-11-04 15:34:19.13507+00	2026-11-04 15:34:19.135075+00
\.


--
-- Data for Name: company_officials; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.company_officials (company_id, person_name, role, role_title, nip, position_sk_number, is_active, id, created_at, updated_at) FROM stdin;
171aeb4a-3fba-42c8-ba1a-f11989994835	Bambang Solifian	DIREKTUR	Direktur	\N	Akta Notaris No. 12 Th 2020	t	f94317cd-1763-4397-a66c-86b0a9b801de	2026-11-04 15:34:19.139632+00	2026-11-04 15:34:19.139637+00
c7f238aa-49a6-4909-8a5d-a882f2461b09	Ir. H. Gunawan Wibisono	DIREKTUR	Direktur Utama	\N	Akta Notaris No. 88 Th 2021	t	e4f2a4b0-fc4a-422e-8e82-049efa3c1afc	2026-11-04 15:34:19.485652+00	2026-11-04 15:34:19.485658+00
\.


--
-- Data for Name: document_events; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.document_events (revision_id, event_code, event_date, day_name_id, location, notes, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: document_numbers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.document_numbers (revision_id, doc_code, doc_number, issuer, counter_val, issue_date, is_reserved, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: findings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.findings (run_id, rule_code, severity, doc_code, sheet_name, cell_range, field_name, original_value, proposed_value, message, disposition, disposition_reason, disposition_actor, id, created_at, updated_at) FROM stdin;
0ee0d99b-02f9-4022-b7a8-f0c4cf78edb7	BR02	BLOCK	D01	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D01' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	e727bf98-e5ef-47f9-9862-1a1ef7b47e13	2026-11-04 16:37:48.220304+00	2026-11-04 16:37:48.220313+00
0ee0d99b-02f9-4022-b7a8-f0c4cf78edb7	BR02	BLOCK	D02	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D02' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	69fe82c2-cf48-4d49-9e77-9bf6e92caf1a	2026-11-04 16:37:48.22032+00	2026-11-04 16:37:48.220322+00
0ee0d99b-02f9-4022-b7a8-f0c4cf78edb7	BR02	BLOCK	D03	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D03' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	988583c5-1ad8-48b2-aac7-a730c281f1c0	2026-11-04 16:37:48.220327+00	2026-11-04 16:37:48.220328+00
0ee0d99b-02f9-4022-b7a8-f0c4cf78edb7	BR02	BLOCK	D04	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D04' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	b7b09955-bf51-4805-b227-b2c4c55e6bf2	2026-11-04 16:37:48.220334+00	2026-11-04 16:37:48.220335+00
0ee0d99b-02f9-4022-b7a8-f0c4cf78edb7	BR02	BLOCK	D05	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D05' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	e73b6edd-cdd2-408d-bd39-2a7c29866ea5	2026-11-04 16:37:48.22034+00	2026-11-04 16:37:48.220342+00
0ee0d99b-02f9-4022-b7a8-f0c4cf78edb7	BR02	BLOCK	D06	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D06' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	48d2f7fc-57b8-4755-af39-6d776fc57495	2026-11-04 16:37:48.220347+00	2026-11-04 16:37:48.220348+00
0ee0d99b-02f9-4022-b7a8-f0c4cf78edb7	BR02	BLOCK	D07	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D07' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	b9b3d2a5-a69b-4f02-86d1-9b30806750a1	2026-11-04 16:37:48.220353+00	2026-11-04 16:37:48.220354+00
0ee0d99b-02f9-4022-b7a8-f0c4cf78edb7	BR02	BLOCK	D08	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D08' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	cae1e008-d05b-4321-8a1b-21e628ebf461	2026-11-04 16:37:48.220359+00	2026-11-04 16:37:48.22036+00
0ee0d99b-02f9-4022-b7a8-f0c4cf78edb7	BR02	BLOCK	D09	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D09' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	e5ecc683-f88c-4243-afc2-a4a8afdaf3ab	2026-11-04 16:37:48.220364+00	2026-11-04 16:37:48.220366+00
0ee0d99b-02f9-4022-b7a8-f0c4cf78edb7	BR02	BLOCK	D10	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D10' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	43af4466-1ad9-456b-b6e3-168424f34280	2026-11-04 16:37:48.220371+00	2026-11-04 16:37:48.220372+00
0ee0d99b-02f9-4022-b7a8-f0c4cf78edb7	BR02	BLOCK	D11	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D11' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	8000e65e-ba6f-40b2-b8ea-601c4db4361e	2026-11-04 16:37:48.220378+00	2026-11-04 16:37:48.220379+00
0ee0d99b-02f9-4022-b7a8-f0c4cf78edb7	BR02	BLOCK	D12	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D12' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	bc83af1a-60ea-4c14-ae58-741590b58866	2026-11-04 16:37:48.220384+00	2026-11-04 16:37:48.220385+00
0ee0d99b-02f9-4022-b7a8-f0c4cf78edb7	BR02	BLOCK	D13	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D13' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	a1dd66bd-93ba-4e05-9038-2d46120f7ffc	2026-11-04 16:37:48.22039+00	2026-11-04 16:37:48.220391+00
0ee0d99b-02f9-4022-b7a8-f0c4cf78edb7	BR06	BLOCK	\N	\N	\N	tax_policy_snapshot	\N	\N	Tidak ada kebijakan perpajakan aktif (tax policy) yang ditetapkan pada snapshot revisi.	PENDING	\N	\N	21688adc-032a-4982-8d1a-63f1cda46cf1	2026-11-04 16:37:48.220395+00	2026-11-04 16:37:48.220396+00
0ee0d99b-02f9-4022-b7a8-f0c4cf78edb7	BR05	BLOCK	\N	\N	\N	subtotal	385000.0000	355000.00000000	Selisih subtotal barang: jumlah total seluruh baris adalah 355000.00000000, namun subtotal tercatat 385000.0000.	PENDING	\N	\N	e99776a3-a205-4b83-b79c-5aef7dcd11fa	2026-11-04 16:37:48.220401+00	2026-11-04 16:37:48.220403+00
0ee0d99b-02f9-4022-b7a8-f0c4cf78edb7	BR05	BLOCK	\N	\N	\N	grand_total	427350.0000	355000.00000000	Selisih total akhir (Grand Total): hasil perhitungan subtotal + pajak aditif adalah 355000.00000000, namun total tercatat 427350.0000.	PENDING	\N	\N	969882c9-faed-4223-a2e7-b596bb1397e0	2026-11-04 16:37:48.220438+00	2026-11-04 16:37:48.22044+00
0ee0d99b-02f9-4022-b7a8-f0c4cf78edb7	BR09	BLOCK	\N	\N	\N	signatory_bendahara	\N	\N	Pejabat sekolah dengan peran 'BENDAHARA' belum ditetapkan pada snapshot revisi.	PENDING	\N	\N	62bb4e9a-f713-4639-93e1-d7dbd2d1e0ef	2026-11-04 16:37:48.220449+00	2026-11-04 16:37:48.22045+00
0ee0d99b-02f9-4022-b7a8-f0c4cf78edb7	BR09	BLOCK	\N	\N	\N	signatory_pengurus_barang	\N	\N	Pejabat sekolah dengan peran 'PENGURUS_BARANG' belum ditetapkan pada snapshot revisi.	PENDING	\N	\N	4abf3b46-305b-4615-929c-20141fe5a420	2026-11-04 16:37:48.220455+00	2026-11-04 16:37:48.220457+00
0ee0d99b-02f9-4022-b7a8-f0c4cf78edb7	BR11	WARNING	\N	\N	\N	lines[1].description	pembersih porselen	porstex	Peringatan diskrepansi teks baris 1: deskripsi sumber 'pembersih porselen' berbeda dengan nama kanonikal terkonfirmasi 'porstex'.	PENDING	\N	\N	4ed6cc6a-d286-4425-9443-95ab8a06a23d	2026-11-04 16:37:48.220462+00	2026-11-04 16:37:48.220464+00
6d25d9a0-277f-4686-9c16-94c5f80ba539	AI_SEMANTIC_DISCREPANCY	WARNING	D01	D01	\N	description	Pembersih Porselen	Variasi pada D05: Konfirmasi kesepakatan merek dagang hasil klarifikasi harga.	[BRAND_SUBSTITUTION] D01 menyebutkan 'Pembersih Porselen', sedangkan D05 menyebutkan merek 'Porstex'.	RESOLVED	Superseded by new AI audit run	\N	46efade6-6c26-4ac5-9b5b-1da6c43f4913	2026-11-04 14:46:35.480738+00	2026-11-04 16:38:04.044907+00
dddff3b0-e1c3-4294-8f1a-3f28e5f28f09	AI_SEMANTIC_DISCREPANCY	WARNING	D01	D01	\N	description	Pembersih Porselen / Porstex	Variasi pada D05: Auditor merekomendasikan untuk meminta klarifikasi tertulis kepada unit pengadaan. Jika penggunaan merek 'Porstex' wajib, pastikan bahwa harga dan spesifikasi yang diajukan sesuai dengan standar kebutuhan sekolah. Jika tidak wajib, ubah kembali ke deskripsi generik atau minta penawaran dari beberapa merek kompetitor.	[BRAND_SUBSTITUTION] Terdapat perbedaan signifikan pada nama item. Dokumen D01 mencantumkan deskripsi generik ('Pembersih Porselen'), sedangkan Dokumen D05 menggunakan nama merek dagang spesifik ('Porstex'). Meskipun spesifikasi volume (Botol 1 Liter) konsisten, substitusi dari produk umum ke merek tertentu harus diverifikasi.	PENDING	\N	\N	f6bc99a2-9f37-4efb-83cc-de8d0e20fe5e	2026-11-04 16:38:04.062865+00	2026-11-04 16:38:04.062868+00
4b57a1b7-668f-44e6-a9f4-e9f164c88551	BR02	BLOCK	D01	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D01' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	580a7654-75ac-4df8-96d3-a13d8e0cfa4e	2026-11-04 16:38:04.120751+00	2026-11-04 16:38:04.120755+00
4b57a1b7-668f-44e6-a9f4-e9f164c88551	BR02	BLOCK	D02	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D02' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	27d5acb1-935e-41ed-a7f0-e4ecffb0963a	2026-11-04 16:38:04.12076+00	2026-11-04 16:38:04.120761+00
4b57a1b7-668f-44e6-a9f4-e9f164c88551	BR02	BLOCK	D03	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D03' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	0ebefcde-bcf1-48da-8ec3-fbe02b3d7421	2026-11-04 16:38:04.120764+00	2026-11-04 16:38:04.120765+00
4b57a1b7-668f-44e6-a9f4-e9f164c88551	BR02	BLOCK	D04	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D04' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	960635f0-ea89-4e06-8dec-1af9bfbdb0ba	2026-11-04 16:38:04.120767+00	2026-11-04 16:38:04.120768+00
4b57a1b7-668f-44e6-a9f4-e9f164c88551	BR02	BLOCK	D05	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D05' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	94e5add2-b8c1-46c8-9782-e7b53a800efa	2026-11-04 16:38:04.120771+00	2026-11-04 16:38:04.120772+00
4b57a1b7-668f-44e6-a9f4-e9f164c88551	BR02	BLOCK	D06	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D06' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	8bfa74ff-b681-47a5-8f83-9638b772389a	2026-11-04 16:38:04.120775+00	2026-11-04 16:38:04.120775+00
4b57a1b7-668f-44e6-a9f4-e9f164c88551	BR02	BLOCK	D07	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D07' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	26fb9511-6b61-4fe4-b560-48386374ef3d	2026-11-04 16:38:04.120778+00	2026-11-04 16:38:04.120779+00
4b57a1b7-668f-44e6-a9f4-e9f164c88551	BR02	BLOCK	D08	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D08' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	f8d31b3a-dff5-4e41-bdd6-0b1815751d40	2026-11-04 16:38:04.120782+00	2026-11-04 16:38:04.120783+00
4b57a1b7-668f-44e6-a9f4-e9f164c88551	BR02	BLOCK	D09	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D09' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	a1c9781b-b15b-43e1-b758-28c09b1ad845	2026-11-04 16:38:04.120786+00	2026-11-04 16:38:04.120787+00
4b57a1b7-668f-44e6-a9f4-e9f164c88551	BR02	BLOCK	D10	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D10' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	630d71fd-9f42-4259-afa9-e050c91a38da	2026-11-04 16:38:04.120789+00	2026-11-04 16:38:04.12079+00
4b57a1b7-668f-44e6-a9f4-e9f164c88551	BR02	BLOCK	D11	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D11' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	9033c593-d618-4738-9e1c-160484efb64c	2026-11-04 16:38:04.120793+00	2026-11-04 16:38:04.120794+00
4b57a1b7-668f-44e6-a9f4-e9f164c88551	BR02	BLOCK	D12	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D12' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	e9f1a08d-7645-49cc-a292-f32a32975b9d	2026-11-04 16:38:04.120797+00	2026-11-04 16:38:04.120844+00
4b57a1b7-668f-44e6-a9f4-e9f164c88551	BR02	BLOCK	D13	\N	\N	doc_number	\N	\N	Nomor dokumen untuk jenis 'D13' belum dialokasikan atau belum terdaftar.	PENDING	\N	\N	9e0787c7-4812-401b-b7e9-0db63bede2c8	2026-11-04 16:38:04.120854+00	2026-11-04 16:38:04.120855+00
4b57a1b7-668f-44e6-a9f4-e9f164c88551	BR06	BLOCK	\N	\N	\N	tax_policy_snapshot	\N	\N	Tidak ada kebijakan perpajakan aktif (tax policy) yang ditetapkan pada snapshot revisi.	PENDING	\N	\N	e9789611-b66c-4cd5-9a5f-25647fc04be5	2026-11-04 16:38:04.120859+00	2026-11-04 16:38:04.12086+00
4b57a1b7-668f-44e6-a9f4-e9f164c88551	BR05	BLOCK	\N	\N	\N	subtotal	385000.0000	355000.00000000	Selisih subtotal barang: jumlah total seluruh baris adalah 355000.00000000, namun subtotal tercatat 385000.0000.	PENDING	\N	\N	4b279d9e-d1a6-4639-a304-29dc80724371	2026-11-04 16:38:04.120862+00	2026-11-04 16:38:04.120863+00
4b57a1b7-668f-44e6-a9f4-e9f164c88551	BR05	BLOCK	\N	\N	\N	grand_total	427350.0000	355000.00000000	Selisih total akhir (Grand Total): hasil perhitungan subtotal + pajak aditif adalah 355000.00000000, namun total tercatat 427350.0000.	PENDING	\N	\N	1f812b72-51e5-4719-9924-4f69752d800e	2026-11-04 16:38:04.120866+00	2026-11-04 16:38:04.120867+00
4b57a1b7-668f-44e6-a9f4-e9f164c88551	BR09	BLOCK	\N	\N	\N	signatory_bendahara	\N	\N	Pejabat sekolah dengan peran 'BENDAHARA' belum ditetapkan pada snapshot revisi.	PENDING	\N	\N	d7be429d-d1da-416f-92d4-976738661656	2026-11-04 16:38:04.12087+00	2026-11-04 16:38:04.12087+00
4b57a1b7-668f-44e6-a9f4-e9f164c88551	BR09	BLOCK	\N	\N	\N	signatory_pengurus_barang	\N	\N	Pejabat sekolah dengan peran 'PENGURUS_BARANG' belum ditetapkan pada snapshot revisi.	PENDING	\N	\N	85104f14-2c8e-4a76-bdd4-01731249f1fc	2026-11-04 16:38:04.120873+00	2026-11-04 16:38:04.120874+00
4b57a1b7-668f-44e6-a9f4-e9f164c88551	BR11	WARNING	\N	\N	\N	lines[1].description	pembersih porselen	porstex	Peringatan diskrepansi teks baris 1: deskripsi sumber 'pembersih porselen' berbeda dengan nama kanonikal terkonfirmasi 'porstex'.	PENDING	\N	\N	df9d260a-7494-4418-995a-d5635da5984a	2026-11-04 16:38:04.120878+00	2026-11-04 16:38:04.120878+00
\.


--
-- Data for Name: funding_sources; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.funding_sources (code, name, description, is_active, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: generation_jobs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.generation_jobs (revision_id, status, progress_percent, error_message, started_at, completed_at, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: imports; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.imports (original_filename, file_hash, file_size, uploaded_at, uploader, status, candidate_payload, sheet_metadata, detected_discrepancies, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: items; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.items (sku, canonical_description, default_spec, brand, category, default_unit, is_active, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: logistics_evidence; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.logistics_evidence (revision_id, file_path, original_filename, file_size, mime_type, sha256_hash, evidence_type, description, uploaded_by, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: logistics_records; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.logistics_records (revision_id, dispatch_date, receipt_date, delivery_reference, courier_name, vehicle_plate, inspection_status, inspection_notes, inspected_by, inspected_at, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: number_counters; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.number_counters (scope_key, counter_val, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: numbering_policies; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.numbering_policies (doc_code, issuer, pattern, reset_period, is_active, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: official_appointments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.official_appointments (school_id, person_name, nip, role, position_sk_number, valid_from, valid_to, is_active, id, created_at, updated_at) FROM stdin;
d581323b-aca5-4b19-9a44-1f1c13eea8f3	Drs. H. Mulyadi, M.Pd	196501011990031005	KEPALA_SEKOLAH	800/014/SK/2025	2025-01-01	\N	t	902c36ce-f835-4cc2-af49-e8568ce04ba3	2026-11-04 15:34:19.098487+00	2026-11-04 15:34:19.098493+00
d581323b-aca5-4b19-9a44-1f1c13eea8f3	Siti Rahmawati, S.Pd	198005122008012015	BENDAHARA	800/015/SK/2025	2025-01-01	\N	t	13295690-8ecc-49c1-a85f-0371d5c08fd5	2026-11-04 15:34:19.098499+00	2026-11-04 15:34:19.0985+00
d581323b-aca5-4b19-9a44-1f1c13eea8f3	Sulistiawati	197909092022212008	PENGURUS_BARANG	800/016/SK/2025	2025-01-01	\N	t	89f47f51-236a-4adc-bbdb-08ca4a5605fd	2026-11-04 15:34:19.098511+00	2026-11-04 15:34:19.098512+00
9df2bdf7-6a07-46ff-9817-76b4d87d7879	Dra. Hj. Nurjanah, M.Pd	196703151992032004	KEPALA_SEKOLAH	800/041/SK-DISDIK/2025	2025-01-01	\N	t	7572fe3d-4777-42f3-9517-7e652c5724e5	2026-11-04 15:34:19.137193+00	2026-11-04 15:34:19.137198+00
9df2bdf7-6a07-46ff-9817-76b4d87d7879	Rahmat Hidayat, S.E	198506202010011018	BENDAHARA	800/042/SK-DISDIK/2025	2025-01-01	\N	t	dad8d739-febf-42bf-91ed-c48a0d4110a4	2026-11-04 15:34:19.137203+00	2026-11-04 15:34:19.137203+00
9df2bdf7-6a07-46ff-9817-76b4d87d7879	Tri Wahyuni, A.Md	199011122019032007	PENGURUS_BARANG	800/043/SK-DISDIK/2025	2025-01-01	\N	t	4c17ba07-7377-4fad-b259-dd0f03dd40fd	2026-11-04 15:34:19.137209+00	2026-11-04 15:34:19.13721+00
\.


--
-- Data for Name: package_profiles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.package_profiles (code, name, description, required_doc_codes, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: package_revisions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.package_revisions (package_id, revision_number, version, status, ai_review_status, school_snapshot, company_snapshot, tax_policy_snapshot, officials_snapshot, subtotal, tax_total, grand_total, terbilang_grand_total, is_locked, notes, id, created_at, updated_at) FROM stdin;
78207c23-6e34-4152-910f-de39515878bc	1	1	DRAFT	COMPLETED	{"name": "SD NEGERI KEBON KOSONG 09", "npsn": "20101234"}	{"legal_name": "CV. PUSTAKA CEMERLANG INDONESIA", "director_name": "Bambang Solifian"}	[]	[{"role": "KEPALA_SEKOLAH", "name": "Drs. H. Mulyono", "nip": "197505101998031002"}]	385000.0000	42350.0000	427350.0000	Empat Ratus Dua Puluh Tujuh Ribu Tiga Ratus Lima Puluh Rupiah	f	\N	29d0bea0-adea-4845-8049-e9d826515973	2026-11-04 14:46:35.423947+00	2026-11-04 14:46:35.482741+00
\.


--
-- Data for Name: packages; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.packages (package_number, school_id, fiscal_year, quarter, funding_source_id, budget_id, current_revision_id, status, id, created_at, updated_at) FROM stdin;
PKG/2026/Q2/4A40	d581323b-aca5-4b19-9a44-1f1c13eea8f3	2026	2	\N	\N	\N	ACTIVE	78207c23-6e34-4152-910f-de39515878bc	2026-11-04 14:46:35.419275+00	2026-11-04 14:46:35.419279+00
\.


--
-- Data for Name: revision_lines; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.revision_lines (revision_id, line_number, item_id, original_description, confirmed_description, specification, quantity, received_quantity, unit, hps_unit_price, offer_unit_price, final_unit_price, discount, line_total, condition, notes, id, created_at, updated_at) FROM stdin;
29d0bea0-adea-4845-8049-e9d826515973	1	\N	Pembersih Porselen	Porstex	Botol 1 Liter	10.0000	10.0000	Botol	24000.0000	23000.0000	22000.0000	0.0000	220000.0000	BAIK	\N	d4c17281-3129-461e-af81-bd759aa6be03	2026-11-04 14:46:35.428045+00	2026-11-04 14:46:35.428051+00
29d0bea0-adea-4845-8049-e9d826515973	2	\N	Pembersih Debu	Pembersih Debu	Pcs	5.0000	5.0000	Pcs	29000.0000	28000.0000	27000.0000	0.0000	135000.0000	BAIK	\N	464438f4-3572-4f7a-a996-360fa1f630f5	2026-11-04 14:46:35.428056+00	2026-11-04 14:46:35.428056+00
\.


--
-- Data for Name: schools; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.schools (name, npsn, level, address, subdistrict, postal_code, email, phone, letterhead_path, is_active, id, created_at, updated_at) FROM stdin;
SD NEGERI KEBON KOSONG 09	20101234	SD	Jl. Kemayoran Gempol no.32	\N	\N	sdnkk09@gmail.com	\N	/storage/uploads/letterheads/schools/kop_sekolah.png	t	d581323b-aca5-4b19-9a44-1f1c13eea8f3	2026-11-04 14:46:35.417119+00	2026-11-04 15:34:19.088462+00
SDN CEMPAKA PUTIH BARAT 01	20104321	SD	Jl. Percetakan Negara IX No. 5	Cempaka Putih	10520	\N	\N	\N	t	9df2bdf7-6a07-46ff-9817-76b4d87d7879	2026-11-04 15:34:19.094823+00	2026-11-04 15:34:19.094831+00
\.


--
-- Data for Name: tax_policy_versions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tax_policy_versions (policy_id, version, tax_type, rate, is_inclusive, withholding_rule, rounding_rule, effective_from, effective_to, is_active, id, created_at, updated_at) FROM stdin;
DEFAULT_2026	1	PPN	0.11000000	f	NONE	ROUND_HALF_UP	2020-01-01	\N	t	e20bc0b8-4b96-4d6b-8064-978a6c177a9d	2026-11-04 15:34:23.530886+00	2026-11-04 15:34:23.530892+00
DEFAULT_2026	1	PPH22	0.01500000	f	WITHHOLD_FROM_PAYABLE	ROUND_HALF_UP	2020-01-01	\N	t	613b0691-76c4-4d97-88bf-5c2fdfd446e9	2026-11-04 15:34:23.530902+00	2026-11-04 15:34:23.530903+00
\.


--
-- Data for Name: units; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.units (code, display_label, allowed_fractional, id, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (username, email, full_name, password_hash, role, is_active, last_login_at, id, created_at, updated_at) FROM stdin;
admin	administrasi@pci.co.id	Staf Administrasi Pengadaan	pbkdf2_sha256$260000$8786a00de2a68da9aff016de4eb8909c$bcd10e2951b887da6a8cddce88a4f67cd2aa65c5e8472a7e1675636f397e11b9	ADMINISTRATION	t	\N	ce21a78a-e37b-4dc6-bb39-4c1fbc0db319	2026-11-04 15:34:19.487932+00	2026-11-04 15:34:19.487933+00
direktur	direktur@pci.co.id	Bambang Solifian	pbkdf2_sha256$260000$da72899af1905ed07f9304f17fa72fe0$67078c095046b0893da8d901178fd552299ed6d5c7c62bb8398e818ede26a2c0	FINANCE_DIRECTOR	t	\N	d31d6f24-40c3-4e70-99e3-3ee5bbed09bd	2026-11-04 15:34:19.487936+00	2026-11-04 15:34:19.487937+00
logistik	logistik@pci.co.id	Petugas Logistik & Pengiriman	pbkdf2_sha256$260000$5b29aa240ae9df92d660b1dbbd4dbe3d$edbe8994d3b90e0bcb3b9ea2b2aec50ed66b3935ffa9811fe9c3350fbc8b2580	LOGISTICS	t	\N	21e3d635-bd3d-443c-9f17-bdd9af1d3858	2026-11-04 15:34:19.48794+00	2026-11-04 15:34:19.487941+00
sysadmin	sysadmin@pci.co.id	Administrator Sistem	pbkdf2_sha256$260000$f3bbb5f22e75ca2df836252d4fdff277$6b1500795cc519eecae02850da26d6d19c805fbce5ae5fd15997e620527f4797	SYSTEM_ADMINISTRATOR	t	2026-11-04 16:39:19.009636+00	6eba36a5-0c2e-4ab9-96b9-aec8e917ab4e	2026-11-04 15:34:19.487923+00	2026-11-04 16:39:19.012117+00
\.


--
-- Data for Name: validation_runs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.validation_runs (revision_id, triggered_by, run_at, passed, error_count, warning_count, info_count, id, created_at, updated_at) FROM stdin;
29d0bea0-adea-4845-8049-e9d826515973	AI_ADVISOR	2026-11-04 14:46:35.473593+00	t	0	1	0	6d25d9a0-277f-4686-9c16-94c5f80ba539	2026-11-04 14:46:35.473615+00	2026-11-04 14:46:35.473618+00
29d0bea0-adea-4845-8049-e9d826515973	SYSTEM_ADMINISTRATOR	2026-11-04 16:37:48.207851+00	f	18	1	0	0ee0d99b-02f9-4022-b7a8-f0c4cf78edb7	2026-11-04 16:37:48.207914+00	2026-11-04 16:37:48.207919+00
29d0bea0-adea-4845-8049-e9d826515973	AI_ADVISOR	2026-11-04 16:38:04.054162+00	t	0	1	0	dddff3b0-e1c3-4294-8f1a-3f28e5f28f09	2026-11-04 16:38:04.054182+00	2026-11-04 16:38:04.054185+00
29d0bea0-adea-4845-8049-e9d826515973	SYSTEM_ADMINISTRATOR	2026-11-04 16:38:04.117158+00	f	18	1	0	4b57a1b7-668f-44e6-a9f4-e9f164c88551	2026-11-04 16:38:04.11718+00	2026-11-04 16:38:04.117184+00
\.


--
-- Name: ai_usage_logs ai_usage_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ai_usage_logs
    ADD CONSTRAINT ai_usage_logs_pkey PRIMARY KEY (id);


--
-- Name: approvals approvals_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.approvals
    ADD CONSTRAINT approvals_pkey PRIMARY KEY (id);


--
-- Name: archive_records archive_records_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.archive_records
    ADD CONSTRAINT archive_records_pkey PRIMARY KEY (id);


--
-- Name: artifacts artifacts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.artifacts
    ADD CONSTRAINT artifacts_pkey PRIMARY KEY (id);


--
-- Name: audit_events audit_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_events
    ADD CONSTRAINT audit_events_pkey PRIMARY KEY (id);


--
-- Name: budget_classifications budget_classifications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.budget_classifications
    ADD CONSTRAINT budget_classifications_pkey PRIMARY KEY (id);


--
-- Name: companies companies_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_pkey PRIMARY KEY (id);


--
-- Name: company_officials company_officials_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company_officials
    ADD CONSTRAINT company_officials_pkey PRIMARY KEY (id);


--
-- Name: document_events document_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.document_events
    ADD CONSTRAINT document_events_pkey PRIMARY KEY (id);


--
-- Name: document_numbers document_numbers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.document_numbers
    ADD CONSTRAINT document_numbers_pkey PRIMARY KEY (id);


--
-- Name: findings findings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.findings
    ADD CONSTRAINT findings_pkey PRIMARY KEY (id);


--
-- Name: funding_sources funding_sources_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.funding_sources
    ADD CONSTRAINT funding_sources_pkey PRIMARY KEY (id);


--
-- Name: generation_jobs generation_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.generation_jobs
    ADD CONSTRAINT generation_jobs_pkey PRIMARY KEY (id);


--
-- Name: imports imports_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.imports
    ADD CONSTRAINT imports_pkey PRIMARY KEY (id);


--
-- Name: items items_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.items
    ADD CONSTRAINT items_pkey PRIMARY KEY (id);


--
-- Name: logistics_evidence logistics_evidence_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.logistics_evidence
    ADD CONSTRAINT logistics_evidence_pkey PRIMARY KEY (id);


--
-- Name: logistics_records logistics_records_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.logistics_records
    ADD CONSTRAINT logistics_records_pkey PRIMARY KEY (id);


--
-- Name: number_counters number_counters_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.number_counters
    ADD CONSTRAINT number_counters_pkey PRIMARY KEY (id);


--
-- Name: numbering_policies numbering_policies_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.numbering_policies
    ADD CONSTRAINT numbering_policies_pkey PRIMARY KEY (id);


--
-- Name: official_appointments official_appointments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.official_appointments
    ADD CONSTRAINT official_appointments_pkey PRIMARY KEY (id);


--
-- Name: package_profiles package_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.package_profiles
    ADD CONSTRAINT package_profiles_pkey PRIMARY KEY (id);


--
-- Name: package_revisions package_revisions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.package_revisions
    ADD CONSTRAINT package_revisions_pkey PRIMARY KEY (id);


--
-- Name: packages packages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.packages
    ADD CONSTRAINT packages_pkey PRIMARY KEY (id);


--
-- Name: revision_lines revision_lines_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.revision_lines
    ADD CONSTRAINT revision_lines_pkey PRIMARY KEY (id);


--
-- Name: schools schools_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.schools
    ADD CONSTRAINT schools_pkey PRIMARY KEY (id);


--
-- Name: tax_policy_versions tax_policy_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tax_policy_versions
    ADD CONSTRAINT tax_policy_versions_pkey PRIMARY KEY (id);


--
-- Name: units units_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.units
    ADD CONSTRAINT units_pkey PRIMARY KEY (id);


--
-- Name: package_revisions uq_package_revision; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.package_revisions
    ADD CONSTRAINT uq_package_revision UNIQUE (package_id, revision_number);


--
-- Name: tax_policy_versions uq_policy_ver_type; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tax_policy_versions
    ADD CONSTRAINT uq_policy_ver_type UNIQUE (policy_id, version, tax_type);


--
-- Name: document_numbers uq_revision_doc_number; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.document_numbers
    ADD CONSTRAINT uq_revision_doc_number UNIQUE (revision_id, doc_code);


--
-- Name: document_events uq_revision_event_code; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.document_events
    ADD CONSTRAINT uq_revision_event_code UNIQUE (revision_id, event_code);


--
-- Name: revision_lines uq_revision_line_num; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.revision_lines
    ADD CONSTRAINT uq_revision_line_num UNIQUE (revision_id, line_number);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: validation_runs validation_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.validation_runs
    ADD CONSTRAINT validation_runs_pkey PRIMARY KEY (id);


--
-- Name: ix_ai_usage_logs_provider; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ai_usage_logs_provider ON public.ai_usage_logs USING btree (provider);


--
-- Name: ix_ai_usage_logs_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ai_usage_logs_status ON public.ai_usage_logs USING btree (status);


--
-- Name: ix_ai_usage_logs_task_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ai_usage_logs_task_type ON public.ai_usage_logs USING btree (task_type);


--
-- Name: ix_approvals_revision_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_approvals_revision_id ON public.approvals USING btree (revision_id);


--
-- Name: ix_archive_records_package_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_archive_records_package_id ON public.archive_records USING btree (package_id);


--
-- Name: ix_archive_records_revision_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_archive_records_revision_id ON public.archive_records USING btree (revision_id);


--
-- Name: ix_archive_records_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_archive_records_status ON public.archive_records USING btree (status);


--
-- Name: ix_artifacts_job_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_artifacts_job_id ON public.artifacts USING btree (job_id);


--
-- Name: ix_artifacts_revision_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_artifacts_revision_id ON public.artifacts USING btree (revision_id);


--
-- Name: ix_audit_events_action; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_audit_events_action ON public.audit_events USING btree (action);


--
-- Name: ix_audit_events_entity_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_audit_events_entity_id ON public.audit_events USING btree (entity_id);


--
-- Name: ix_audit_events_entity_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_audit_events_entity_name ON public.audit_events USING btree (entity_name);


--
-- Name: ix_budget_classifications_fiscal_year; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_budget_classifications_fiscal_year ON public.budget_classifications USING btree (fiscal_year);


--
-- Name: ix_document_events_revision_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_document_events_revision_id ON public.document_events USING btree (revision_id);


--
-- Name: ix_document_numbers_revision_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_document_numbers_revision_id ON public.document_numbers USING btree (revision_id);


--
-- Name: ix_findings_rule_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_findings_rule_code ON public.findings USING btree (rule_code);


--
-- Name: ix_findings_run_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_findings_run_id ON public.findings USING btree (run_id);


--
-- Name: ix_funding_sources_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_funding_sources_code ON public.funding_sources USING btree (code);


--
-- Name: ix_generation_jobs_revision_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_generation_jobs_revision_id ON public.generation_jobs USING btree (revision_id);


--
-- Name: ix_generation_jobs_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_generation_jobs_status ON public.generation_jobs USING btree (status);


--
-- Name: ix_imports_file_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_imports_file_hash ON public.imports USING btree (file_hash);


--
-- Name: ix_items_canonical_description; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_items_canonical_description ON public.items USING btree (canonical_description);


--
-- Name: ix_items_sku; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_items_sku ON public.items USING btree (sku);


--
-- Name: ix_logistics_evidence_revision_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_logistics_evidence_revision_id ON public.logistics_evidence USING btree (revision_id);


--
-- Name: ix_logistics_records_revision_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_logistics_records_revision_id ON public.logistics_records USING btree (revision_id);


--
-- Name: ix_number_counters_scope_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_number_counters_scope_key ON public.number_counters USING btree (scope_key);


--
-- Name: ix_numbering_policies_doc_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_numbering_policies_doc_code ON public.numbering_policies USING btree (doc_code);


--
-- Name: ix_package_profiles_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_package_profiles_code ON public.package_profiles USING btree (code);


--
-- Name: ix_package_revisions_ai_review_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_package_revisions_ai_review_status ON public.package_revisions USING btree (ai_review_status);


--
-- Name: ix_package_revisions_package_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_package_revisions_package_id ON public.package_revisions USING btree (package_id);


--
-- Name: ix_package_revisions_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_package_revisions_status ON public.package_revisions USING btree (status);


--
-- Name: ix_packages_fiscal_year; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_packages_fiscal_year ON public.packages USING btree (fiscal_year);


--
-- Name: ix_packages_package_number; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_packages_package_number ON public.packages USING btree (package_number);


--
-- Name: ix_packages_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_packages_status ON public.packages USING btree (status);


--
-- Name: ix_revision_lines_revision_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_revision_lines_revision_id ON public.revision_lines USING btree (revision_id);


--
-- Name: ix_schools_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_schools_name ON public.schools USING btree (name);


--
-- Name: ix_schools_npsn; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_schools_npsn ON public.schools USING btree (npsn);


--
-- Name: ix_tax_policy_versions_policy_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tax_policy_versions_policy_id ON public.tax_policy_versions USING btree (policy_id);


--
-- Name: ix_units_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_units_code ON public.units USING btree (code);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_role; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_role ON public.users USING btree (role);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: ix_validation_runs_revision_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_validation_runs_revision_id ON public.validation_runs USING btree (revision_id);


--
-- Name: approvals approvals_revision_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.approvals
    ADD CONSTRAINT approvals_revision_id_fkey FOREIGN KEY (revision_id) REFERENCES public.package_revisions(id) ON DELETE CASCADE;


--
-- Name: archive_records archive_records_package_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.archive_records
    ADD CONSTRAINT archive_records_package_id_fkey FOREIGN KEY (package_id) REFERENCES public.packages(id) ON DELETE CASCADE;


--
-- Name: archive_records archive_records_revision_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.archive_records
    ADD CONSTRAINT archive_records_revision_id_fkey FOREIGN KEY (revision_id) REFERENCES public.package_revisions(id) ON DELETE CASCADE;


--
-- Name: artifacts artifacts_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.artifacts
    ADD CONSTRAINT artifacts_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.generation_jobs(id) ON DELETE SET NULL;


--
-- Name: artifacts artifacts_revision_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.artifacts
    ADD CONSTRAINT artifacts_revision_id_fkey FOREIGN KEY (revision_id) REFERENCES public.package_revisions(id) ON DELETE CASCADE;


--
-- Name: company_officials company_officials_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company_officials
    ADD CONSTRAINT company_officials_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- Name: document_events document_events_revision_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.document_events
    ADD CONSTRAINT document_events_revision_id_fkey FOREIGN KEY (revision_id) REFERENCES public.package_revisions(id) ON DELETE CASCADE;


--
-- Name: document_numbers document_numbers_revision_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.document_numbers
    ADD CONSTRAINT document_numbers_revision_id_fkey FOREIGN KEY (revision_id) REFERENCES public.package_revisions(id) ON DELETE CASCADE;


--
-- Name: findings findings_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.findings
    ADD CONSTRAINT findings_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.validation_runs(id) ON DELETE CASCADE;


--
-- Name: generation_jobs generation_jobs_revision_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.generation_jobs
    ADD CONSTRAINT generation_jobs_revision_id_fkey FOREIGN KEY (revision_id) REFERENCES public.package_revisions(id) ON DELETE CASCADE;


--
-- Name: logistics_evidence logistics_evidence_revision_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.logistics_evidence
    ADD CONSTRAINT logistics_evidence_revision_id_fkey FOREIGN KEY (revision_id) REFERENCES public.package_revisions(id) ON DELETE CASCADE;


--
-- Name: logistics_records logistics_records_revision_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.logistics_records
    ADD CONSTRAINT logistics_records_revision_id_fkey FOREIGN KEY (revision_id) REFERENCES public.package_revisions(id) ON DELETE CASCADE;


--
-- Name: official_appointments official_appointments_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.official_appointments
    ADD CONSTRAINT official_appointments_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.schools(id) ON DELETE CASCADE;


--
-- Name: package_revisions package_revisions_package_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.package_revisions
    ADD CONSTRAINT package_revisions_package_id_fkey FOREIGN KEY (package_id) REFERENCES public.packages(id) ON DELETE CASCADE;


--
-- Name: packages packages_budget_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.packages
    ADD CONSTRAINT packages_budget_id_fkey FOREIGN KEY (budget_id) REFERENCES public.budget_classifications(id) ON DELETE SET NULL;


--
-- Name: packages packages_funding_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.packages
    ADD CONSTRAINT packages_funding_source_id_fkey FOREIGN KEY (funding_source_id) REFERENCES public.funding_sources(id) ON DELETE SET NULL;


--
-- Name: packages packages_school_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.packages
    ADD CONSTRAINT packages_school_id_fkey FOREIGN KEY (school_id) REFERENCES public.schools(id) ON DELETE RESTRICT;


--
-- Name: revision_lines revision_lines_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.revision_lines
    ADD CONSTRAINT revision_lines_item_id_fkey FOREIGN KEY (item_id) REFERENCES public.items(id) ON DELETE SET NULL;


--
-- Name: revision_lines revision_lines_revision_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.revision_lines
    ADD CONSTRAINT revision_lines_revision_id_fkey FOREIGN KEY (revision_id) REFERENCES public.package_revisions(id) ON DELETE CASCADE;


--
-- Name: validation_runs validation_runs_revision_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.validation_runs
    ADD CONSTRAINT validation_runs_revision_id_fkey FOREIGN KEY (revision_id) REFERENCES public.package_revisions(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict oIhOd1p6kumzQFgFaqwZHb5IqnbMqrjlrKgrAavomUENwU03jrnJKhr8lZWsZLH

