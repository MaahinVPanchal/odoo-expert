SET maintenance_work_mem = '128MB';
CREATE INDEX idx_odoo_docs_version ON odoo_docs (version);

CREATE INDEX idx_odoo_docs_embedding ON odoo_docs
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 328);
