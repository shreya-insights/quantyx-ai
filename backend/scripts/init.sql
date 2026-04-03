-- Quantyx AI — MySQL 8.0 initialization script
-- Seeds default categories for merchant classification

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- Insert default merchant categories (MCC-style codes)
INSERT IGNORE INTO categories (name, code, parent_id) VALUES
  ('Groceries',           'GROC', NULL),
  ('Restaurants',         'REST', NULL),
  ('Transportation',      'TRAN', NULL),
  ('Healthcare',          'HLTH', NULL),
  ('Entertainment',       'ENTM', NULL),
  ('Shopping',            'SHOP', NULL),
  ('Utilities',           'UTIL', NULL),
  ('Travel',              'TRVL', NULL),
  ('Financial Services',  'FNSV', NULL),
  ('Education',           'EDUC', NULL),
  ('Gas & Fuel',          'FUEL', NULL),
  ('Online Services',     'ONLN', NULL),
  ('ATM & Cash',          'CASH', NULL),
  ('Gambling',            'GMBL', NULL),
  ('Other',               'OTHR', NULL);
