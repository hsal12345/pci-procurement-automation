"""0001_initial_baseline

Revision ID: 0001_initial_baseline
Revises: 
Create Date: 2026-09-13 23:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from app.models.base import GUID

# revision identifiers, used by Alembic.
revision: str = '0001_initial_baseline'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. companies
    op.create_table(
        'companies',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('legal_name', sa.String(255), nullable=False),
        sa.Column('npwp', sa.String(32), nullable=True),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('subdistrict', sa.String(100), nullable=True),
        sa.Column('city', sa.String(100), nullable=False, server_default="Jakarta"),
        sa.Column('postal_code', sa.String(16), nullable=True),
        sa.Column('email', sa.String(128), nullable=True),
        sa.Column('phone', sa.String(32), nullable=True),
        sa.Column('bank_name', sa.String(100), nullable=True),
        sa.Column('bank_account_number', sa.String(64), nullable=True),
        sa.Column('bank_account_holder', sa.String(255), nullable=True),
        sa.Column('director_name', sa.String(255), nullable=False),
        sa.Column('director_title', sa.String(100), nullable=False, server_default="Direktur"),
        sa.Column('logo_path', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 2. schools
    op.create_table(
        'schools',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('npsn', sa.String(16), nullable=True, unique=True),
        sa.Column('level', sa.String(16), nullable=False, server_default="SD"),
        sa.Column('address', sa.Text(), nullable=False),
        sa.Column('subdistrict', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(16), nullable=True),
        sa.Column('email', sa.String(128), nullable=True),
        sa.Column('phone', sa.String(32), nullable=True),
        sa.Column('letterhead_path', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_schools_name', 'schools', ['name'])

    # 3. official_appointments
    op.create_table(
        'official_appointments',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('school_id', GUID(), sa.ForeignKey('schools.id', ondelete='CASCADE'), nullable=False),
        sa.Column('person_name', sa.String(255), nullable=False),
        sa.Column('nip', sa.String(32), nullable=True),
        sa.Column('role', sa.String(64), nullable=False),
        sa.Column('valid_from', sa.Date(), nullable=False),
        sa.Column('valid_to', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 4. items
    op.create_table(
        'items',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('sku', sa.String(64), nullable=True, unique=True),
        sa.Column('canonical_description', sa.String(255), nullable=False),
        sa.Column('default_spec', sa.Text(), nullable=True),
        sa.Column('brand', sa.String(100), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('default_unit', sa.String(32), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_items_canonical_desc', 'items', ['canonical_description'])

    # 5. units
    op.create_table(
        'units',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('code', sa.String(32), unique=True, nullable=False),
        sa.Column('display_label', sa.String(64), nullable=False),
        sa.Column('allowed_fractional', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 6. budget_classifications
    op.create_table(
        'budget_classifications',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('fiscal_year', sa.Integer(), nullable=False),
        sa.Column('activity_code', sa.String(64), nullable=True),
        sa.Column('activity_name', sa.String(255), nullable=False),
        sa.Column('sub_activity', sa.String(255), nullable=True),
        sa.Column('account_code', sa.String(64), nullable=True),
        sa.Column('account_name', sa.String(255), nullable=False),
        sa.Column('funding_source_code', sa.String(32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 7. funding_sources
    op.create_table(
        'funding_sources',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('code', sa.String(32), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 8. tax_policy_versions
    op.create_table(
        'tax_policy_versions',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('policy_id', sa.String(64), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default="1"),
        sa.Column('tax_type', sa.String(32), nullable=False),
        sa.Column('rate', sa.Numeric(12, 8), nullable=False),
        sa.Column('is_inclusive', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('withholding_rule', sa.String(64), nullable=False, server_default="NONE"),
        sa.Column('rounding_rule', sa.String(32), nullable=False, server_default="ROUND_HALF_UP"),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('policy_id', 'version', 'tax_type', name='uq_policy_ver_type')
    )

    # 9. package_profiles
    op.create_table(
        'package_profiles',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('code', sa.String(64), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('required_doc_codes', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 10. numbering_policies
    op.create_table(
        'numbering_policies',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('doc_code', sa.String(32), nullable=False),
        sa.Column('issuer', sa.String(32), nullable=False),
        sa.Column('pattern', sa.String(128), nullable=False),
        sa.Column('reset_period', sa.String(32), nullable=False, server_default="YEARLY"),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 11. number_counters (concurrency-safe counter table)
    op.create_table(
        'number_counters',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('scope_key', sa.String(64), unique=True, nullable=False),
        sa.Column('counter_val', sa.Integer(), nullable=False, server_default="0"),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 12. packages
    op.create_table(
        'packages',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('package_number', sa.String(64), unique=True, nullable=False),
        sa.Column('school_id', GUID(), sa.ForeignKey('schools.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('fiscal_year', sa.Integer(), nullable=False),
        sa.Column('quarter', sa.Integer(), nullable=False),
        sa.Column('funding_source_id', GUID(), sa.ForeignKey('funding_sources.id', ondelete='SET NULL'), nullable=True),
        sa.Column('budget_id', GUID(), sa.ForeignKey('budget_classifications.id', ondelete='SET NULL'), nullable=True),
        sa.Column('current_revision_id', GUID(), nullable=True),
        sa.Column('status', sa.String(32), nullable=False, server_default="DRAFT"),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_packages_status', 'packages', ['status'])

    # 13. package_revisions
    op.create_table(
        'package_revisions',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('package_id', GUID(), sa.ForeignKey('packages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('revision_number', sa.Integer(), nullable=False, server_default="1"),
        sa.Column('version', sa.Integer(), nullable=False, server_default="1"),
        sa.Column('school_snapshot', sa.JSON(), nullable=False),
        sa.Column('company_snapshot', sa.JSON(), nullable=False),
        sa.Column('tax_policy_snapshot', sa.JSON(), nullable=False),
        sa.Column('officials_snapshot', sa.JSON(), nullable=False),
        sa.Column('subtotal', sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column('tax_total', sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column('grand_total', sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column('terbilang_grand_total', sa.Text(), nullable=True),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('package_id', 'revision_number', name='uq_package_revision')
    )

    # 14. revision_lines (with 3 prices: hps_unit_price, offer_unit_price, final_unit_price)
    op.create_table(
        'revision_lines',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('revision_id', GUID(), sa.ForeignKey('package_revisions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('line_number', sa.Integer(), nullable=False),
        sa.Column('item_id', GUID(), sa.ForeignKey('items.id', ondelete='SET NULL'), nullable=True),
        sa.Column('original_description', sa.Text(), nullable=False),
        sa.Column('confirmed_description', sa.Text(), nullable=False),
        sa.Column('specification', sa.Text(), nullable=True),
        sa.Column('quantity', sa.Numeric(18, 4), nullable=False),
        sa.Column('unit', sa.String(32), nullable=False),
        sa.Column('hps_unit_price', sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column('offer_unit_price', sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column('final_unit_price', sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column('discount', sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column('line_total', sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column('condition', sa.String(32), nullable=False, server_default="BAIK"),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('revision_id', 'line_number', name='uq_revision_line_num')
    )

    # 15. document_events
    op.create_table(
        'document_events',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('revision_id', GUID(), sa.ForeignKey('package_revisions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_code', sa.String(32), nullable=False),
        sa.Column('event_date', sa.Date(), nullable=False),
        sa.Column('day_name_id', sa.String(32), nullable=True),
        sa.Column('location', sa.String(100), nullable=False, server_default="Jakarta"),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('revision_id', 'event_code', name='uq_revision_event_code')
    )

    # 16. document_numbers
    op.create_table(
        'document_numbers',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('revision_id', GUID(), sa.ForeignKey('package_revisions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('doc_code', sa.String(32), nullable=False),
        sa.Column('doc_number', sa.String(128), nullable=False),
        sa.Column('issuer', sa.String(32), nullable=False),
        sa.Column('counter_val', sa.Integer(), nullable=True),
        sa.Column('issue_date', sa.Date(), nullable=True),
        sa.Column('is_reserved', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('revision_id', 'doc_code', name='uq_revision_doc_number')
    )

    # 17. validation_runs
    op.create_table(
        'validation_runs',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('revision_id', GUID(), sa.ForeignKey('package_revisions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('triggered_by', sa.String(100), nullable=True),
        sa.Column('run_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default="0"),
        sa.Column('warning_count', sa.Integer(), nullable=False, server_default="0"),
        sa.Column('info_count', sa.Integer(), nullable=False, server_default="0"),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 18. findings
    op.create_table(
        'findings',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('run_id', GUID(), sa.ForeignKey('validation_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rule_code', sa.String(16), nullable=False),
        sa.Column('severity', sa.String(16), nullable=False),
        sa.Column('doc_code', sa.String(32), nullable=True),
        sa.Column('sheet_name', sa.String(64), nullable=True),
        sa.Column('cell_range', sa.String(32), nullable=True),
        sa.Column('field_name', sa.String(100), nullable=True),
        sa.Column('original_value', sa.Text(), nullable=True),
        sa.Column('proposed_value', sa.Text(), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('disposition', sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column('disposition_reason', sa.Text(), nullable=True),
        sa.Column('disposition_actor', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 19. generation_jobs
    op.create_table(
        'generation_jobs',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('revision_id', GUID(), sa.ForeignKey('package_revisions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default="QUEUED"),
        sa.Column('progress_percent', sa.Integer(), nullable=False, server_default="0"),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 20. artifacts
    op.create_table(
        'artifacts',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('job_id', GUID(), sa.ForeignKey('generation_jobs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('revision_id', GUID(), sa.ForeignKey('package_revisions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('doc_code', sa.String(32), nullable=True),
        sa.Column('format', sa.String(16), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(512), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False, server_default="0"),
        sa.Column('sha256_hash', sa.String(64), nullable=False),
        sa.Column('is_draft', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('archive_status', sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 21. approvals
    op.create_table(
        'approvals',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('revision_id', GUID(), sa.ForeignKey('package_revisions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('approver_name', sa.String(255), nullable=False),
        sa.Column('approver_role', sa.String(64), nullable=False, server_default="FINANCE_DIRECTOR"),
        sa.Column('decision', sa.String(32), nullable=False),
        sa.Column('decision_reason', sa.Text(), nullable=True),
        sa.Column('reviewed_manifest_hash', sa.String(64), nullable=True),
        sa.Column('signed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 22. audit_events
    op.create_table(
        'audit_events',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('entity_name', sa.String(64), nullable=False),
        sa.Column('entity_id', sa.String(64), nullable=False),
        sa.Column('action', sa.String(32), nullable=False),
        sa.Column('actor', sa.String(100), nullable=False, server_default="system"),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('before_state', sa.JSON(), nullable=True),
        sa.Column('after_state', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(64), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_audit_events_entity', 'audit_events', ['entity_name', 'entity_id'])

    # 23. imports
    op.create_table(
        'imports',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('file_hash', sa.String(64), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False, server_default="0"),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('uploader', sa.String(100), nullable=False, server_default="admin"),
        sa.Column('status', sa.String(32), nullable=False, server_default="PARSED"),
        sa.Column('candidate_payload', sa.JSON(), nullable=True),
        sa.Column('sheet_metadata', sa.JSON(), nullable=True),
        sa.Column('detected_discrepancies', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_imports_file_hash', 'imports', ['file_hash'])


def downgrade() -> None:
    op.drop_table('imports')
    op.drop_table('audit_events')
    op.drop_table('approvals')
    op.drop_table('artifacts')
    op.drop_table('generation_jobs')
    op.drop_table('findings')
    op.drop_table('validation_runs')
    op.drop_table('document_numbers')
    op.drop_table('document_events')
    op.drop_table('revision_lines')
    op.drop_table('package_revisions')
    op.drop_table('packages')
    op.drop_table('number_counters')
    op.drop_table('numbering_policies')
    op.drop_table('package_profiles')
    op.drop_table('tax_policy_versions')
    op.drop_table('funding_sources')
    op.drop_table('budget_classifications')
    op.drop_table('units')
    op.drop_table('items')
    op.drop_table('official_appointments')
    op.drop_table('schools')
    op.drop_table('companies')
