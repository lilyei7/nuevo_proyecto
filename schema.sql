-- SQLite schema for hotel scraping

CREATE TABLE IF NOT EXISTS hotels (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  hotel_id TEXT NOT NULL,
  source_domain TEXT NOT NULL,
  hotel_name TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(hotel_id, source_domain)
);

CREATE TABLE IF NOT EXISTS scrapes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  hotel_id_fk INTEGER REFERENCES hotels(id) ON DELETE CASCADE,
  checkin DATE NOT NULL,
  checkout DATE NOT NULL,
  price_amount REAL NULL,
  price_currency TEXT NULL,
  availability TEXT NOT NULL,
  status_code INTEGER NULL,
  attempt_count INTEGER DEFAULT 0,
  user_agent TEXT,
  source_url TEXT,
  scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  notes TEXT,
  UNIQUE(hotel_id_fk, checkin)
);

CREATE INDEX IF NOT EXISTS idx_scrapes_scraped_at ON scrapes(scraped_at);
CREATE INDEX IF NOT EXISTS idx_scrapes_hotel_checkin ON scrapes(hotel_id_fk, checkin);
