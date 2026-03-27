-- =============================================================================
-- StreamRev Database Schema
-- Generated from SQLAlchemy domain models (src/domain/models.py)
-- Target: MySQL 8.0+ / MariaDB 10.5+
-- =============================================================================

SET FOREIGN_KEY_CHECKS = 0;
SET NAMES utf8mb4;

-- ---------------------------------------------------------------------------
-- TABLES
-- ---------------------------------------------------------------------------

CREATE TABLE access_codes (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	code VARCHAR(255) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	type INTEGER NOT NULL, 
	enabled BOOL NOT NULL, 
	max_connections INTEGER NOT NULL, 
	allowed_ips TEXT, 
	allowed_uas TEXT, 
	allowed_countries TEXT, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);

CREATE TABLE blocked_asns (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	asn INTEGER NOT NULL, 
	isp VARCHAR(256), 
	domain VARCHAR(256), 
	country VARCHAR(16), 
	num_ips INTEGER NOT NULL, 
	type VARCHAR(64), 
	blocked BOOL NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (asn)
);

CREATE TABLE blocked_ips (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	ip VARCHAR(64) NOT NULL, 
	reason TEXT, 
	enabled BOOL NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE blocked_isps (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	isp_name VARCHAR(512) NOT NULL, 
	enabled BOOL NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE blocked_uas (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	pattern VARCHAR(512) NOT NULL, 
	enabled BOOL NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE bouquets (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	bouquet_name VARCHAR(255) NOT NULL, 
	bouquet_channels TEXT NOT NULL, 
	bouquet_movies TEXT NOT NULL, 
	bouquet_radios TEXT NOT NULL, 
	bouquet_series TEXT NOT NULL, 
	bouquet_order INTEGER NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE client_logs (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER, 
	stream_id INTEGER, 
	event VARCHAR(128) NOT NULL, 
	ip VARCHAR(64), 
	data TEXT, 
	date DATETIME NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE hmac_keys (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	`key` TEXT NOT NULL, 
	notes TEXT, 
	enabled BOOL NOT NULL, 
	allowed_ips TEXT, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE migrations (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	migration VARCHAR(255) NOT NULL, 
	applied_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (migration)
);

CREATE TABLE profiles (
	profile_id INTEGER NOT NULL AUTO_INCREMENT, 
	profile_name VARCHAR(255) NOT NULL, 
	profile_command TEXT, 
	profile_type VARCHAR(32) NOT NULL, 
	enabled BOOL NOT NULL, 
	PRIMARY KEY (profile_id)
);

CREATE TABLE reg_users (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	username VARCHAR(255) NOT NULL, 
	password TEXT NOT NULL, 
	email VARCHAR(255), 
	ip VARCHAR(64), 
	status INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE resellers (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	username VARCHAR(255) NOT NULL, 
	password TEXT NOT NULL, 
	owner_id INTEGER, 
	credits INTEGER NOT NULL, 
	notes TEXT, 
	status INTEGER NOT NULL, 
	allowed_ips TEXT, 
	max_credits INTEGER, 
	allowed_packages TEXT, 
	PRIMARY KEY (id), 
	UNIQUE (username), 
	FOREIGN KEY(owner_id) REFERENCES resellers (id) ON DELETE SET NULL
);

CREATE TABLE servers (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	server_name VARCHAR(255) NOT NULL, 
	server_ip VARCHAR(255) NOT NULL, 
	server_hardware_id VARCHAR(255), 
	domain_name VARCHAR(255), 
	http_port INTEGER NOT NULL, 
	https_port INTEGER NOT NULL, 
	rtmp_port INTEGER NOT NULL, 
	server_protocol VARCHAR(16) NOT NULL, 
	vpn_ip VARCHAR(255), 
	total_clients INTEGER NOT NULL, 
	is_main BOOL NOT NULL, 
	status INTEGER NOT NULL, 
	parent_id INTEGER, 
	network_guaranteed_speed INTEGER, 
	total_bandwidth_usage INTEGER, 
	ssh_port INTEGER NOT NULL, 
	ssh_user VARCHAR(128), 
	ssh_password TEXT, 
	server_key TEXT, 
	timeshift_path TEXT, 
	rtmp_path TEXT, 
	enable_geoip BOOL NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(parent_id) REFERENCES servers (id) ON DELETE SET NULL
);

CREATE TABLE settings (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	`key` VARCHAR(255) NOT NULL, 
	value TEXT, 
	type VARCHAR(16) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (`key`)
);

CREATE TABLE stream_categories (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	category_name VARCHAR(255) NOT NULL, 
	category_type VARCHAR(32) NOT NULL, 
	parent_id INTEGER, 
	`order` INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(parent_id) REFERENCES stream_categories (id) ON DELETE SET NULL
);

CREATE TABLE stream_types (
	type_id INTEGER NOT NULL AUTO_INCREMENT, 
	type_name VARCHAR(64) NOT NULL, 
	type_key VARCHAR(64) NOT NULL, 
	type_output VARCHAR(64) NOT NULL, 
	live BOOL NOT NULL, 
	PRIMARY KEY (type_id)
);

CREATE TABLE users_groups (
	group_id INTEGER NOT NULL AUTO_INCREMENT, 
	group_name VARCHAR(255) NOT NULL, 
	can_delete BOOL NOT NULL, 
	packages TEXT, 
	PRIMARY KEY (group_id)
);

CREATE TABLE movies (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	stream_display_name VARCHAR(512) NOT NULL, 
	stream_source TEXT NOT NULL, 
	stream_icon TEXT, 
	rating VARCHAR(32), 
	rating_5based FLOAT, 
	category_id INTEGER, 
	container_extension VARCHAR(16) NOT NULL, 
	custom_sid VARCHAR(255), 
	added DATETIME NOT NULL, 
	direct_source BOOL NOT NULL, 
	target_container VARCHAR(16) NOT NULL, 
	tmdb_id INTEGER, 
	plot TEXT, 
	cast TEXT, 
	director VARCHAR(255), 
	genre VARCHAR(255), 
	release_date VARCHAR(32), 
	episode_run_time INTEGER, 
	youtube_trailer TEXT, 
	backdrop_path TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(category_id) REFERENCES stream_categories (id) ON DELETE SET NULL
);

CREATE TABLE packages (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	package_name VARCHAR(255) NOT NULL, 
	is_trial BOOL NOT NULL, 
	is_official BOOL NOT NULL, 
	trial_credits INTEGER NOT NULL, 
	official_credits INTEGER NOT NULL, 
	trial_duration INTEGER NOT NULL, 
	official_duration INTEGER NOT NULL, 
	max_connections INTEGER NOT NULL, 
	allowed_bouquets TEXT NOT NULL, 
	allowed_output_types TEXT NOT NULL, 
	can_general_edit BOOL NOT NULL, 
	activity_type VARCHAR(64), 
	only_mag BOOL NOT NULL, 
	only_enigma BOOL NOT NULL, 
	force_server_id INTEGER, 
	max_sub_resellers INTEGER NOT NULL, 
	only_stalker BOOL NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(force_server_id) REFERENCES servers (id) ON DELETE SET NULL
);

CREATE TABLE proxies (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	proxy_name VARCHAR(255) NOT NULL, 
	proxy_url TEXT NOT NULL, 
	proxy_type VARCHAR(32) NOT NULL, 
	proxy_username VARCHAR(255), 
	proxy_password VARCHAR(255), 
	enabled BOOL NOT NULL, 
	server_id INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(server_id) REFERENCES servers (id) ON DELETE SET NULL
);

CREATE TABLE series (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	title VARCHAR(512) NOT NULL, 
	category_id INTEGER, 
	cover TEXT, 
	plot TEXT, 
	cast TEXT, 
	director VARCHAR(255), 
	genre VARCHAR(255), 
	release_date VARCHAR(32), 
	rating VARCHAR(32), 
	rating_5based FLOAT, 
	backdrop_path TEXT, 
	youtube_trailer TEXT, 
	tmdb_id INTEGER, 
	last_modified DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(category_id) REFERENCES stream_categories (id) ON DELETE SET NULL
);

CREATE TABLE streams (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	stream_display_name VARCHAR(512) NOT NULL, 
	stream_source TEXT NOT NULL, 
	stream_icon TEXT, 
	epg_channel_id VARCHAR(255), 
	added DATETIME NOT NULL, 
	category_id INTEGER, 
	custom_ffmpeg TEXT, 
	custom_sid VARCHAR(255), 
	stream_all BOOL NOT NULL, 
	type INTEGER NOT NULL, 
	target_container VARCHAR(16) NOT NULL, 
	enabled BOOL NOT NULL, 
	direct_source BOOL NOT NULL, 
	notes TEXT, 
	read_native BOOL NOT NULL, 
	allow_record BOOL NOT NULL, 
	probed_resolution VARCHAR(64), 
	current_source INTEGER NOT NULL, 
	tv_archive BOOL NOT NULL, 
	tv_archive_duration INTEGER, 
	tv_archive_server_id INTEGER, 
	transcode_profile_id INTEGER, 
	`order` INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(category_id) REFERENCES stream_categories (id) ON DELETE SET NULL, 
	FOREIGN KEY(tv_archive_server_id) REFERENCES servers (id) ON DELETE SET NULL, 
	FOREIGN KEY(transcode_profile_id) REFERENCES profiles (profile_id) ON DELETE SET NULL
);

CREATE TABLE users (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	username VARCHAR(255) NOT NULL, 
	password TEXT NOT NULL, 
	player_api_token VARCHAR(128), 
	exp_date DATETIME, 
	max_connections INTEGER NOT NULL, 
	is_trial BOOL NOT NULL, 
	is_admin BOOL NOT NULL, 
	enabled BOOL NOT NULL, 
	admin_notes TEXT, 
	reseller_notes TEXT, 
	created_at DATETIME NOT NULL, 
	allowed_ips TEXT, 
	allowed_user_agents TEXT, 
	is_restreamer BOOL NOT NULL, 
	force_server_id INTEGER, 
	bouquet TEXT, 
	allowed_output_ids TEXT, 
	is_stalker BOOL NOT NULL, 
	is_mag BOOL NOT NULL, 
	created_by_reseller_id INTEGER, 
	member_group_id INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (username), 
	UNIQUE (player_api_token), 
	FOREIGN KEY(force_server_id) REFERENCES servers (id) ON DELETE SET NULL, 
	FOREIGN KEY(created_by_reseller_id) REFERENCES resellers (id) ON DELETE SET NULL, 
	FOREIGN KEY(member_group_id) REFERENCES users_groups (group_id) ON DELETE SET NULL
);

CREATE TABLE enigma2_devices (
	device_id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER NOT NULL, 
	mac VARCHAR(32) NOT NULL, 
	original_mac VARCHAR(32), 
	modem_mac VARCHAR(32), 
	token VARCHAR(255), 
	key_auth TEXT, 
	local_ip VARCHAR(64), 
	public_ip VARCHAR(64), 
	enigma_version VARCHAR(128), 
	cpu VARCHAR(128), 
	version VARCHAR(64), 
	lversion TEXT, 
	dns VARCHAR(255), 
	lock_device BOOL NOT NULL, 
	watchdog_timeout INTEGER NOT NULL, 
	last_updated INTEGER, 
	rc TEXT, 
	enabled BOOL NOT NULL, 
	PRIMARY KEY (device_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE epg_data (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	epg_id VARCHAR(255), 
	title VARCHAR(512) NOT NULL, 
	lang VARCHAR(16), 
	start DATETIME NOT NULL, 
	end DATETIME NOT NULL, 
	description TEXT, 
	channel_id INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(channel_id) REFERENCES streams (id) ON DELETE CASCADE
);

CREATE TABLE `lines` (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER NOT NULL, 
	server_id INTEGER NOT NULL, 
	stream_id INTEGER NOT NULL, 
	container VARCHAR(16) NOT NULL, 
	pid INTEGER, 
	date DATETIME NOT NULL, 
	user_agent TEXT, 
	user_ip VARCHAR(64), 
	geoip_country_code VARCHAR(8), 
	bitrate INTEGER, 
	external_device TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(server_id) REFERENCES servers (id) ON DELETE CASCADE, 
	FOREIGN KEY(stream_id) REFERENCES streams (id) ON DELETE CASCADE
);

CREATE TABLE mag_devices (
	mag_id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER NOT NULL, 
	mac VARCHAR(32) NOT NULL, 
	sn VARCHAR(128), 
	model VARCHAR(128), 
	ip VARCHAR(64), 
	ver VARCHAR(64), 
	stb_type VARCHAR(64), 
	token VARCHAR(255), 
	lock_device BOOL NOT NULL, 
	last_updated INTEGER, 
	enabled BOOL NOT NULL, 
	PRIMARY KEY (mag_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE series_episodes (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	series_id INTEGER NOT NULL, 
	season_number INTEGER NOT NULL, 
	episode_number INTEGER NOT NULL, 
	stream_display_name VARCHAR(512) NOT NULL, 
	stream_source TEXT NOT NULL, 
	container_extension VARCHAR(16) NOT NULL, 
	custom_sid VARCHAR(255), 
	added DATETIME NOT NULL, 
	direct_source BOOL NOT NULL, 
	tmdb_id INTEGER, 
	plot TEXT, 
	duration INTEGER, 
	rating VARCHAR(32), 
	movie_image TEXT, 
	bitrate INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(series_id) REFERENCES series (id) ON DELETE CASCADE
);

CREATE TABLE server_streams (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	server_id INTEGER NOT NULL, 
	stream_id INTEGER NOT NULL, 
	pid INTEGER, 
	on_demand BOOL NOT NULL, 
	stream_status INTEGER NOT NULL, 
	bitrate INTEGER, 
	current_source INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_server_streams_server_stream UNIQUE (server_id, stream_id), 
	FOREIGN KEY(server_id) REFERENCES servers (id) ON DELETE CASCADE, 
	FOREIGN KEY(stream_id) REFERENCES streams (id) ON DELETE CASCADE
);

CREATE TABLE stream_logs (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	stream_id INTEGER NOT NULL, 
	server_id INTEGER NOT NULL, 
	date DATETIME NOT NULL, 
	info TEXT, 
	type VARCHAR(64), 
	PRIMARY KEY (id), 
	FOREIGN KEY(stream_id) REFERENCES streams (id) ON DELETE CASCADE, 
	FOREIGN KEY(server_id) REFERENCES servers (id) ON DELETE CASCADE
);

CREATE TABLE tickets (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	title VARCHAR(512) NOT NULL, 
	message TEXT, 
	status INTEGER NOT NULL, 
	user_id INTEGER, 
	admin_reply TEXT, 
	priority VARCHAR(32) NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE user_activity (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER NOT NULL, 
	stream_id INTEGER NOT NULL, 
	server_id INTEGER NOT NULL, 
	user_agent TEXT, 
	user_ip VARCHAR(64), 
	container VARCHAR(16) NOT NULL, 
	date_start DATETIME NOT NULL, 
	date_stop DATETIME, 
	geoip_country_code VARCHAR(8), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(stream_id) REFERENCES streams (id) ON DELETE CASCADE, 
	FOREIGN KEY(server_id) REFERENCES servers (id) ON DELETE CASCADE
);

CREATE TABLE enigma2_actions (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	device_id INTEGER NOT NULL, 
	`key` VARCHAR(64) NOT NULL, 
	command TEXT, 
	command2 TEXT, 
	type VARCHAR(64), 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(device_id) REFERENCES enigma2_devices (device_id) ON DELETE CASCADE
);


-- ---------------------------------------------------------------------------
-- INDEXES
-- ---------------------------------------------------------------------------

CREATE INDEX ix_access_codes_enabled ON access_codes (enabled);
CREATE INDEX ix_access_codes_type ON access_codes (type);

CREATE INDEX ix_blocked_asns_blocked ON blocked_asns (blocked);

CREATE INDEX ix_blocked_ips_enabled ON blocked_ips (enabled);
CREATE INDEX ix_blocked_ips_ip ON blocked_ips (ip);

CREATE INDEX ix_blocked_uas_enabled ON blocked_uas (enabled);

CREATE INDEX ix_bouquets_bouquet_order ON bouquets (bouquet_order);

CREATE INDEX ix_client_logs_user_id ON client_logs (user_id);
CREATE INDEX ix_client_logs_date ON client_logs (date);

CREATE INDEX ix_hmac_keys_enabled ON hmac_keys (enabled);

CREATE INDEX ix_profiles_enabled ON profiles (enabled);

CREATE INDEX ix_resellers_status ON resellers (status);
CREATE INDEX ix_resellers_owner_id ON resellers (owner_id);

CREATE INDEX ix_servers_parent_id ON servers (parent_id);
CREATE INDEX ix_servers_status ON servers (status);
CREATE INDEX ix_servers_is_main ON servers (is_main);

CREATE INDEX ix_stream_categories_category_type ON stream_categories (category_type);
CREATE INDEX ix_stream_categories_parent_id ON stream_categories (parent_id);

CREATE INDEX ix_stream_types_type_key ON stream_types (type_key);

CREATE INDEX ix_movies_category_id ON movies (category_id);

CREATE INDEX ix_packages_force_server_id ON packages (force_server_id);

CREATE INDEX ix_proxies_enabled ON proxies (enabled);
CREATE INDEX ix_proxies_server_id ON proxies (server_id);

CREATE INDEX ix_series_category_id ON series (category_id);

CREATE INDEX ix_streams_enabled ON streams (enabled);
CREATE INDEX ix_streams_stream_type ON streams (type);
CREATE INDEX ix_streams_category_id ON streams (category_id);
CREATE INDEX ix_streams_tv_archive_server_id ON streams (tv_archive_server_id);

CREATE INDEX ix_users_member_group_id ON users (member_group_id);
CREATE INDEX ix_users_force_server_id ON users (force_server_id);
CREATE INDEX ix_users_enabled ON users (enabled);

CREATE INDEX ix_enigma2_devices_user_id ON enigma2_devices (user_id);
CREATE INDEX ix_enigma2_devices_mac ON enigma2_devices (mac);
CREATE INDEX ix_enigma2_devices_enabled ON enigma2_devices (enabled);

CREATE INDEX ix_epg_data_epg_id ON epg_data (epg_id);
CREATE INDEX ix_epg_data_start_end ON epg_data (start, end);
CREATE INDEX ix_epg_data_channel_id ON epg_data (channel_id);

CREATE INDEX ix_lines_server_id ON `lines` (server_id);
CREATE INDEX ix_lines_date ON `lines` (date);
CREATE INDEX ix_lines_stream_id ON `lines` (stream_id);
CREATE INDEX ix_lines_user_id ON `lines` (user_id);

CREATE INDEX ix_series_episodes_series_id ON series_episodes (series_id);
CREATE INDEX ix_series_episodes_season_episode ON series_episodes (series_id, season_number, episode_number);

CREATE INDEX ix_server_streams_stream_status ON server_streams (stream_status);
CREATE INDEX ix_server_streams_server_id ON server_streams (server_id);
CREATE INDEX ix_server_streams_stream_id ON server_streams (stream_id);

CREATE INDEX ix_stream_logs_date ON stream_logs (date);
CREATE INDEX ix_stream_logs_server_id ON stream_logs (server_id);
CREATE INDEX ix_stream_logs_stream_id ON stream_logs (stream_id);

CREATE INDEX ix_tickets_user_id ON tickets (user_id);
CREATE INDEX ix_tickets_status ON tickets (status);

CREATE INDEX ix_user_activity_user_id ON user_activity (user_id);
CREATE INDEX ix_user_activity_server_id ON user_activity (server_id);
CREATE INDEX ix_user_activity_date_start ON user_activity (date_start);
CREATE INDEX ix_user_activity_stream_id ON user_activity (stream_id);

CREATE INDEX ix_enigma2_actions_device_id ON enigma2_actions (device_id);


SET FOREIGN_KEY_CHECKS = 1;
