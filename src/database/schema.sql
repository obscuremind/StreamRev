-- StreamRev Database Schema
-- IPTV Backend Platform Database Structure

-- Users Table
CREATE TABLE IF NOT EXISTS `users` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(255) NOT NULL UNIQUE,
  `password` VARCHAR(255) NOT NULL,
  `email` VARCHAR(255),
  `status` TINYINT(1) DEFAULT 1,
  `exp_date` DATETIME NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `admin_enabled` TINYINT(1) DEFAULT 0,
  `admin_notes` TEXT,
  `reseller_id` INT UNSIGNED NULL,
  `owner_id` INT UNSIGNED NULL,
  `bouquet_id` INT UNSIGNED NULL,
  `max_connections` INT DEFAULT 1,
  `is_trial` TINYINT(1) DEFAULT 0,
  `last_ip` VARCHAR(45),
  `last_login` DATETIME NULL,
  PRIMARY KEY (`id`),
  KEY `username_idx` (`username`),
  KEY `reseller_idx` (`reseller_id`),
  KEY `status_idx` (`status`),
  KEY `exp_date_idx` (`exp_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Resellers Table
CREATE TABLE IF NOT EXISTS `resellers` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(255) NOT NULL UNIQUE,
  `password` VARCHAR(255) NOT NULL,
  `email` VARCHAR(255),
  `status` TINYINT(1) DEFAULT 1,
  `credits` DECIMAL(10,2) DEFAULT 0.00,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `parent_id` INT UNSIGNED NULL,
  `permissions` JSON,
  PRIMARY KEY (`id`),
  KEY `username_idx` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Streams (Live TV Channels)
CREATE TABLE IF NOT EXISTS `streams` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `stream_display_name` VARCHAR(255),
  `stream_icon` VARCHAR(500),
  `stream_type` VARCHAR(50) DEFAULT 'live',
  `stream_source` TEXT NOT NULL,
  `category_id` INT UNSIGNED,
  `status` TINYINT(1) DEFAULT 1,
  `order` INT DEFAULT 0,
  `transcode_profile` VARCHAR(100),
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `category_idx` (`category_id`),
  KEY `status_idx` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- VOD (Movies)
CREATE TABLE IF NOT EXISTS `vod` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `title` VARCHAR(255),
  `year` VARCHAR(10),
  `director` VARCHAR(255),
  `cast` TEXT,
  `description` TEXT,
  `plot` TEXT,
  `duration` VARCHAR(20),
  `rating` VARCHAR(10),
  `cover` VARCHAR(500),
  `backdrop` VARCHAR(500),
  `trailer` VARCHAR(500),
  `category_id` INT UNSIGNED,
  `stream_source` TEXT NOT NULL,
  `status` TINYINT(1) DEFAULT 1,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `category_idx` (`category_id`),
  KEY `status_idx` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Series
CREATE TABLE IF NOT EXISTS `series` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `title` VARCHAR(255),
  `year` VARCHAR(10),
  `cast` TEXT,
  `description` TEXT,
  `plot` TEXT,
  `rating` VARCHAR(10),
  `cover` VARCHAR(500),
  `backdrop` VARCHAR(500),
  `trailer` VARCHAR(500),
  `category_id` INT UNSIGNED,
  `status` TINYINT(1) DEFAULT 1,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `category_idx` (`category_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Series Episodes
CREATE TABLE IF NOT EXISTS `series_episodes` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `series_id` INT UNSIGNED NOT NULL,
  `season` INT NOT NULL,
  `episode_num` INT NOT NULL,
  `title` VARCHAR(255),
  `description` TEXT,
  `stream_source` TEXT NOT NULL,
  `cover` VARCHAR(500),
  `duration` VARCHAR(20),
  `status` TINYINT(1) DEFAULT 1,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `series_idx` (`series_id`),
  KEY `season_episode_idx` (`season`, `episode_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Categories
CREATE TABLE IF NOT EXISTS `categories` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `type` VARCHAR(50) NOT NULL,
  `parent_id` INT UNSIGNED NULL,
  `order` INT DEFAULT 0,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `type_idx` (`type`),
  KEY `parent_idx` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- EPG (Electronic Program Guide)
CREATE TABLE IF NOT EXISTS `epg` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `stream_id` INT UNSIGNED NOT NULL,
  `start_time` DATETIME NOT NULL,
  `end_time` DATETIME NOT NULL,
  `title` VARCHAR(255) NOT NULL,
  `description` TEXT,
  `lang` VARCHAR(10),
  PRIMARY KEY (`id`),
  KEY `stream_time_idx` (`stream_id`, `start_time`, `end_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- User Activity Logs
CREATE TABLE IF NOT EXISTS `user_activity` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` INT UNSIGNED NOT NULL,
  `stream_id` INT UNSIGNED,
  `stream_type` VARCHAR(50),
  `action` VARCHAR(100),
  `ip_address` VARCHAR(45),
  `user_agent` TEXT,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `user_idx` (`user_id`),
  KEY `created_idx` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sessions
CREATE TABLE IF NOT EXISTS `sessions` (
  `id` VARCHAR(128) NOT NULL,
  `user_id` INT UNSIGNED NOT NULL,
  `ip_address` VARCHAR(45),
  `user_agent` TEXT,
  `payload` TEXT NOT NULL,
  `last_activity` INT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_idx` (`user_id`),
  KEY `last_activity_idx` (`last_activity`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Server Nodes (Load Balancer)
CREATE TABLE IF NOT EXISTS `server_nodes` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `hostname` VARCHAR(255) NOT NULL,
  `port` INT DEFAULT 80,
  `status` TINYINT(1) DEFAULT 1,
  `type` VARCHAR(50) DEFAULT 'streaming',
  `load` INT DEFAULT 0,
  `max_clients` INT DEFAULT 1000,
  `current_clients` INT DEFAULT 0,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `status_idx` (`status`),
  KEY `type_idx` (`type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Settings
CREATE TABLE IF NOT EXISTS `settings` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `key` VARCHAR(255) NOT NULL UNIQUE,
  `value` TEXT,
  `type` VARCHAR(50) DEFAULT 'string',
  `description` TEXT,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `key_idx` (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default admin user (password: admin123 - CHANGE THIS!)
INSERT INTO `users` (`username`, `password`, `email`, `status`, `admin_enabled`, `max_connections`) 
VALUES ('admin', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'admin@streamrev.local', 1, 1, 10)
ON DUPLICATE KEY UPDATE username=username;

-- Insert default settings
INSERT INTO `settings` (`key`, `value`, `type`, `description`) VALUES
('site_name', 'StreamRev', 'string', 'Site name'),
('ffmpeg_path', '/usr/bin/ffmpeg', 'string', 'Path to FFmpeg binary'),
('redis_host', '127.0.0.1', 'string', 'Redis server host'),
('redis_port', '6379', 'string', 'Redis server port'),
('max_connections_per_user', '1', 'integer', 'Maximum connections per user')
ON DUPLICATE KEY UPDATE `key`=`key`;
