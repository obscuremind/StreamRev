-- =============================================================================
-- StreamRev - Default Admin User Seed
-- Password: StreamRev@2026!   (CHANGE IMMEDIATELY after first login)
-- Uses bcrypt via passlib (same as src/core/auth/password.py)
-- =============================================================================

INSERT INTO users (
    username,
    password,
    exp_date,
    max_connections,
    is_trial,
    is_admin,
    enabled,
    admin_notes,
    is_restreamer,
    is_stalker,
    is_mag,
    created_at
) VALUES (
    'admin',
    '$2b$12$MYSiBEdAkdIzkPprGQM4KenDwPMi6niejICefDW9QDrbVoCAQ3VRa',
    NULL,
    1,
    0,
    1,
    1,
    'Default admin account - change password after first login',
    0,
    0,
    0,
    NOW()
);
