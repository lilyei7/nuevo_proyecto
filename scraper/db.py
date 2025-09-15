import sqlite3
import os
from typing import Optional, Tuple, List, Dict
import datetime
import logging
import threading
import time
from contextlib import contextmanager

# Flask-SocketIO for real-time logging
try:
    from socket_manager import emit_log_message as emit_db_log
    HAVE_SOCKETIO = True
except ImportError:
    HAVE_SOCKETIO = False
    def emit_db_log(*args, **kwargs):
        pass

log = logging.getLogger(__name__)

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEFAULT_DB = os.path.join(repo_root, 'db.sqlite3')


def connect(db_path: str = DEFAULT_DB):
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def create_schema(conn: sqlite3.Connection):
    with conn:
        cursor = conn.cursor()
        sql = open('schema.sql', 'r', encoding='utf-8').read()
        cursor.executescript(sql)


def get_or_create_hotel(conn: sqlite3.Connection, hotel_id: str, source_domain: str, hotel_name: Optional[str] = None) -> int:
    with conn:
        cur = conn.cursor()
        cur.execute('SELECT id FROM hotels WHERE hotel_id = ? AND source_domain = ?', (hotel_id, source_domain))
        row = cur.fetchone()
        if row:
            return row['id']
        cur.execute('INSERT INTO hotels (hotel_id, source_domain, hotel_name) VALUES (?, ?, ?)', (hotel_id, source_domain, hotel_name))
        return cur.lastrowid


def insert_scrape(conn: sqlite3.Connection, hotel_id_fk: int, checkin: str, checkout: str, price_amount: Optional[float], price_currency: Optional[str], availability: str, status_code: Optional[int], attempt_count: int, user_agent: str, source_url: str, notes: Optional[str] = None):
    with conn:
        cur = conn.cursor()
        cur.execute(
            'INSERT OR REPLACE INTO scrapes (hotel_id_fk, checkin, checkout, price_amount, price_currency, availability, status_code, attempt_count, user_agent, source_url, notes, scraped_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)',
            (hotel_id_fk, checkin, checkout, price_amount, price_currency, availability, status_code, attempt_count, user_agent, source_url, notes)
        )
        return cur.lastrowid


class DatabaseManager:
    """Enhanced database manager for Flask app

    By default the DB file is placed in the project root as `hotels.db` so
    the location is stable regardless of the current working directory.
    """

    def __init__(self, db_path: Optional[str] = None):
        # If caller didn't provide a path, force use of the Django project's sqlite DB
        if not db_path:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            db_path = os.path.join(repo_root, 'db.sqlite3')

        # Normalize to an absolute path so the DB location is unambiguous
        # and so we can create parent directories when needed.
        try:
            self.db_path = os.path.abspath(db_path)
        except Exception:
            self.db_path = db_path

        # Ensure parent directory exists (if a directory part was provided)
        parent = os.path.dirname(self.db_path)
        if parent and not os.path.exists(parent):
            try:
                os.makedirs(parent, exist_ok=True)
            except Exception as e:
                log.error(f"Failed to create parent directory for DB ({parent}): {e}")

        # thread-local placeholder (not required but kept for API parity)
        self._local = threading.local()
        self.init_db()
    
    def init_db(self):
        """Initialize database with schema"""
        try:
            with self.get_connection() as conn:
                # Create tables if they don't exist
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS hotels (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        url TEXT NOT NULL UNIQUE,
                        city TEXT,
                        country TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        otasync_property_id TEXT,
                        otasync_room_type_id TEXT,
                        otasync_enabled INTEGER DEFAULT 0
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
                        notes TEXT
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_scrapes_hotel_id ON scrapes (hotel_id_fk);
                    CREATE INDEX IF NOT EXISTS idx_scrapes_dates ON scrapes (checkin, checkout);
                    CREATE INDEX IF NOT EXISTS idx_scrapes_price ON scrapes (price_amount);
                """)
                
                # Add new columns to scrapes table for advanced scraping info
                cursor = conn.cursor()
                scrape_cols = [r[1] for r in cursor.execute("PRAGMA table_info(scrapes)").fetchall()]
                
                # Add base_price column if not exists
                if 'base_price' not in scrape_cols:
                    cursor.execute("ALTER TABLE scrapes ADD COLUMN base_price REAL NULL")
                    log.info("Added base_price column to scrapes table")
                
                # Add margin_percent column if not exists
                if 'margin_percent' not in scrape_cols:
                    cursor.execute("ALTER TABLE scrapes ADD COLUMN margin_percent REAL NULL")
                    log.info("Added margin_percent column to scrapes table")
                
                # Add margin_amount column if not exists
                if 'margin_amount' not in scrape_cols:
                    cursor.execute("ALTER TABLE scrapes ADD COLUMN margin_amount REAL NULL")
                    log.info("Added margin_amount column to scrapes table")
                
                # Add OTASync columns to existing hotels table if they don't exist
                cols = [r[1] for r in cursor.execute("PRAGMA table_info(hotels)").fetchall()]
                
                if 'otasync_property_id' not in cols:
                    cursor.execute("ALTER TABLE hotels ADD COLUMN otasync_property_id TEXT")
                    log.info("Added otasync_property_id column to hotels table")
                
                if 'otasync_room_type_id' not in cols:
                    cursor.execute("ALTER TABLE hotels ADD COLUMN otasync_room_type_id TEXT")
                    log.info("Added otasync_room_type_id column to hotels table")
                    
                if 'otasync_enabled' not in cols:
                    cursor.execute("ALTER TABLE hotels ADD COLUMN otasync_enabled INTEGER DEFAULT 0")
                    log.info("Added otasync_enabled column to hotels table")
                
                if 'price_percent' not in cols:
                    cursor.execute("ALTER TABLE hotels ADD COLUMN price_percent REAL DEFAULT 0.0")
                    log.info("Added price_percent column to hotels table")
                
                log.info("Database initialized successfully")
        except Exception as e:
            log.error(f"Failed to initialize database ({getattr(self, 'db_path', 'unknown')}): {e}")
            raise
    
    def get_connection(self):
        """Get a tuned connection (use same strategy as the main DatabaseManager)."""
        # Keep compatibility but use a tuned connection
        try:
            conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES, timeout=30, check_same_thread=False)
        except sqlite3.OperationalError:
            raise sqlite3.OperationalError(f"unable to open database file: {self.db_path}")
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute("PRAGMA temp_store = MEMORY;")
        except Exception:
            pass
        return conn

    @contextmanager
    def _db_transaction(self, max_retries: int = 5, backoff_base: float = 0.05):
        """Run a transaction with retries on database locks.

        Yields a sqlite3.Connection.
        """
        attempt = 0
        while True:
            attempt += 1
            conn = self.get_connection()
            try:
                conn.execute("BEGIN IMMEDIATE")
                yield conn
                conn.commit()
                try:
                    conn.close()
                except Exception:
                    pass
                return
            except sqlite3.OperationalError as e:
                msg = str(e).lower()
                try:
                    conn.rollback()
                except Exception:
                    pass
                try:
                    conn.close()
                except Exception:
                    pass
                if 'locked' in msg or 'database is locked' in msg:
                    if attempt >= max_retries:
                        log.error(f"DB transaction failed after {attempt} attempts: {e}")
                        raise
                    sleep_for = backoff_base * (2 ** (attempt - 1))
                    time.sleep(sleep_for)
                    continue
                else:
                    raise
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
                try:
                    conn.close()
                except Exception:
                    pass
                raise
    
    # Hotel management
    def insert_hotel(self, name: str, url: str, city: str = None, country: str = None) -> int:
        """Insert new hotel"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO hotels (name, url, city, country)
                VALUES (?, ?, ?, ?)
            """, (name, url, city, country))
            
            if cursor.rowcount == 0:
                # Hotel already exists, get its ID
                cursor.execute("SELECT id FROM hotels WHERE url = ?", (url,))
                return cursor.fetchone()['id']
            
            return cursor.lastrowid
    
    def get_all_hotels(self) -> List[Dict]:
        """Get all hotels"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Check if price_percent column exists and include it if present
            cols = [r[1] for r in cursor.execute("PRAGMA table_info(hotels)").fetchall()]
            select_cols = ['id', 'name', 'url', 'city', 'country', 'created_at', 'otasync_property_id', 'otasync_room_type_id', 'otasync_enabled']
            if 'price_percent' in cols:
                select_cols.append('price_percent')

            sql = f"SELECT {', '.join(select_cols)} FROM hotels ORDER BY created_at DESC"
            cursor.execute(sql)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_hotel_by_id(self, hotel_id: int) -> Optional[Dict]:
        """Get hotel by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cols = [r[1] for r in cursor.execute("PRAGMA table_info(hotels)").fetchall()]
            select_cols = ['id', 'name', 'url', 'city', 'country', 'created_at', 'otasync_property_id', 'otasync_room_type_id', 'otasync_enabled']
            if 'price_percent' in cols:
                select_cols.append('price_percent')

            sql = f"SELECT {', '.join(select_cols)} FROM hotels WHERE id = ?"
            cursor.execute(sql, (hotel_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def delete_hotel(self, hotel_id: int):
        """Delete hotel and associated scrapes"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM hotels WHERE id = ?", (hotel_id,))
            return cursor.rowcount > 0
    
    # Scrape management
    def insert_scrape(self, hotel_id_fk: int, checkin: str, checkout: str, 
                     price_amount: float = None, price_currency: str = 'MXN', 
                     availability: str = 'unknown', status_code: int = None,
                     attempt_count: int = 0, user_agent: str = None, 
                     source_url: str = None, notes: str = None,
                     scraped_at: str = None, base_price: float = None,
                     margin_percent: float = None, margin_amount: float = None,
                     sync_to_otasync: bool = False) -> int:
        """Insert scrape result with all required fields"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            log.info(f"💾 Iniciando guardado en BD: Hotel {hotel_id_fk}, Fecha {checkin}, Precio MXN {price_amount:,.2f}")
            emit_db_log(f"💾 Guardando en BD: Hotel {hotel_id_fk}, Fecha {checkin}, Precio MXN {price_amount:,.2f}", 'info', 'database')
            
            # Si no se proporciona scraped_at, usar la fecha/hora actual
            if not scraped_at:
                scraped_at = datetime.datetime.now().isoformat()
                
            cursor.execute("""
                INSERT INTO scrapes (hotel_id_fk, checkin, checkout, price_amount, price_currency, 
                                   availability, status_code, attempt_count, user_agent, source_url, notes,
                                   scraped_at, base_price, margin_percent, margin_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (hotel_id_fk, checkin, checkout, price_amount, price_currency, 
                  availability, status_code, attempt_count, user_agent, source_url, notes,
                  scraped_at, base_price, margin_percent, margin_amount))
            
            scrape_id = cursor.lastrowid
            log.info(f"💾 Registro guardado exitosamente en BD con ID: {scrape_id}")
            emit_db_log(f"💾 Registro guardado exitosamente en BD (ID: {scrape_id})", 'success', 'database')
            
            # Try to sync price to OTASync if requested, available and price is valid
            if sync_to_otasync and price_amount and availability == 'available':
                log.info(f"🏨 Verificando sincronización con OTASync...")
                emit_db_log(f"🏨 Verificando sincronización con OTASync...", 'info', 'otasync')
                
                try:
                    # Intentamos importar de diferentes ubicaciones
                    try:
                        from otasync_integration import sync_scraped_price_to_otasync
                    except ImportError:
                        # Intentamos con importación relativa desde el directorio principal
                        import sys
                        import os
                        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        from otasync_integration import sync_scraped_price_to_otasync
                    success = sync_scraped_price_to_otasync(
                        hotel_id=hotel_id_fk,
                        checkin_date=checkin,
                        price_amount=price_amount,
                        base_price=price_amount,  # Usar price_amount como base_price
                        taxes=0.0,  # No tenemos taxes en el schema simplificado
                        db_manager=self,
                        log_callback=emit_db_log
                    )
                    if success:
                        log.info(f"✅ Price synced to OTASync for hotel {hotel_id_fk} on {checkin}")
                        emit_db_log(f"✅ Precio sincronizado con OTASync para hotel {hotel_id_fk} en {checkin}", 'success', 'otasync')
                    else:
                        log.debug(f"⚠️ Could not sync price to OTASync for hotel {hotel_id_fk}")
                        emit_db_log(f"⚠️ No se pudo sincronizar precio con OTASync para hotel {hotel_id_fk}", 'warning', 'otasync')
                except ImportError:
                    log.debug("OTASync integration module not available")
                except Exception as e:
                    log.error(f"Error during OTASync sync: {e}")
                    emit_db_log(f"❌ Error durante sincronización con OTASync: {str(e)}", 'error', 'otasync')
            
            return scrape_id
    
    def get_recent_scrapes(self, limit: int = 10) -> List[Dict]:
        """Get recent scrapes with hotel info"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*, h.name as hotel_name
                FROM scrapes s
                JOIN hotels h ON s.hotel_id_fk = h.id
                ORDER BY s.scraped_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_scrapes_by_hotel(self, hotel_id: int) -> List[Dict]:
        """Get all scrapes for a hotel"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*, h.name as hotel_name
                FROM scrapes s
                JOIN hotels h ON s.hotel_id_fk = h.id
                WHERE s.hotel_id_fk = ?
                ORDER BY s.scraped_at DESC
            """, (hotel_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_scrape_by_id(self, scrape_id: int) -> Optional[Dict]:
        """Get a single scrape record by its ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT s.*, h.name as hotel_name
                    FROM scrapes s
                    LEFT JOIN hotels h ON s.hotel_id_fk = h.id
                    WHERE s.id = ?
                    LIMIT 1
                """, (scrape_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            log.error(f"Error getting scrape by id {scrape_id}: {e}")
            return None
    
    def get_scrapes_paginated(self, page: int = 1, per_page: int = 50) -> List[Dict]:
        """Get paginated scrapes"""
        offset = (page - 1) * per_page
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*, h.name as hotel_name
                FROM scrapes s
                JOIN hotels h ON s.hotel_id_fk = h.id
                ORDER BY s.scraped_at DESC
                LIMIT ? OFFSET ?
            """, (per_page, offset))
            return [dict(row) for row in cursor.fetchall()]
    
    # Statistics
    def get_total_scrapes_count(self) -> int:
        """Get total number of scrapes"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM scrapes")
            return cursor.fetchone()['count']
    
    def get_average_price(self) -> Optional[float]:
        """Get average price across all scrapes"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT AVG(price_amount) as avg_price 
                FROM scrapes 
                WHERE price_amount IS NOT NULL AND price_amount > 0
            """)
            result = cursor.fetchone()
            return result['avg_price'] if result and result['avg_price'] else None
    
    def get_last_scrape_date(self) -> Optional[str]:
        """Get date of last scrape"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(scraped_at) as last_date FROM scrapes")
            result = cursor.fetchone()
            return result['last_date'] if result and result['last_date'] else None
    
    def get_price_trends(self) -> List[Dict]:
        """Get price trends over time"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    DATE(scraped_at) as date,
                    AVG(price_amount) as avg_price,
                    MIN(price_amount) as min_price,
                    MAX(price_amount) as max_price,
                    COUNT(*) as scrape_count
                FROM scrapes 
                WHERE price_amount IS NOT NULL AND price_amount > 0
                GROUP BY DATE(scraped_at)
                ORDER BY date DESC
                LIMIT 30
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_hotel_statistics(self) -> List[Dict]:
        """Get statistics by hotel"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    h.name as hotel_name,
                    h.city,
                    COUNT(s.id) as total_scrapes,
                    AVG(s.price_amount) as avg_price,
                    MIN(s.price_amount) as min_price,
                    MAX(s.price_amount) as max_price,
                    MAX(s.scraped_at) as last_scrape
                FROM hotels h
                LEFT JOIN scrapes s ON h.id = s.hotel_id_fk
                GROUP BY h.id, h.name, h.city
                ORDER BY total_scrapes DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    # Additional utility methods
    def clear_all_scrapes(self) -> bool:
        """Clear all scraping data"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM scrapes")
                return True
        except Exception as e:
            log.error(f"Error clearing scrapes: {e}")
            return False

    def get_total_scrapes_count(self) -> int:
        """Get total number of scrapes"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM scrapes")
            row = cursor.fetchone()
            return row['count'] if row else 0

    def get_average_price(self) -> float:
        """Get average price of all available scrapes"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT AVG(price_amount) as avg_price 
                FROM scrapes 
                WHERE price_amount IS NOT NULL AND availability = 'available'
            """)
            row = cursor.fetchone()
            return round(row['avg_price'], 2) if row and row['avg_price'] else None

    def get_last_scrape_date(self) -> str:
        """Get date of last scrape"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(scraped_at) as last_date FROM scrapes")
            row = cursor.fetchone()
            if row and row['last_date']:
                # Format the date nicely
                from datetime import datetime
                date_obj = datetime.fromisoformat(row['last_date'].replace('Z', '+00:00'))
                return date_obj.strftime('%d/%m/%Y %H:%M')
            return None

    def delete_scrape_result(self, scrape_id: int) -> bool:
        """Delete a specific scrape result"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM scrapes WHERE id = ?", (scrape_id,))
                return cursor.rowcount > 0
        except Exception as e:
            log.error(f"Error deleting scrape result {scrape_id}: {e}")
            return False

    def get_hotel_historical_data(self, hotel_id: int) -> List[Dict]:
        """Get historical pricing data for a specific hotel"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT checkin, checkout, price_amount, availability, status_code,
                           attempt_count, user_agent, source_url, notes, scraped_at
                    FROM scrapes 
                    WHERE hotel_id_fk = ? 
                    ORDER BY scraped_at DESC
                    LIMIT 100
                """, (hotel_id,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            log.error(f"Error getting hotel historical data: {e}")
            return []

    def clear_all_scrapes(self) -> bool:
        """Clear all scraping results but keep hotels"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM scrapes")
                log.info(f"Cleared {cursor.rowcount} scrape records")
                return True
        except Exception as e:
            log.error(f"Error clearing all scrapes: {e}")
            return False

    def get_price_trends(self) -> List[Dict]:
        """Get price trends over time"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DATE(scraped_at) as date, 
                           AVG(price_amount) as avg_price,
                           COUNT(*) as count,
                           MIN(price_amount) as min_price,
                           MAX(price_amount) as max_price
                    FROM scrapes 
                    WHERE price_amount IS NOT NULL AND availability = 'available'
                    GROUP BY DATE(scraped_at)
                    ORDER BY date DESC
                    LIMIT 30
                """)
                
                rows = cursor.fetchall()
                trends = []
                for row in rows:
                    trends.append({
                        'date': row['date'],
                        'avg_price': round(row['avg_price'], 2),
                        'min_price': row['min_price'],
                        'max_price': row['max_price'],
                        'count': row['count']
                    })
                
                return trends
        except Exception as e:
            log.error(f"Error getting price trends: {e}")
            return []

    # OTASync integration methods
    def update_hotel_otasync_info(self, hotel_id: int, property_id: str = None, room_type_id: str = None, enabled: bool = None, price_percent: float = None):
        """Update OTASync information for a hotel"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Determine which hotels table exists (Django uses `hotels_hotel`)
            tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            table_name = 'hotels_hotel' if 'hotels_hotel' in tables else 'hotels'

            # Build update query dynamically
            update_fields = []
            values = []

            if property_id is not None:
                update_fields.append("otasync_property_id = ?")
                values.append(property_id)

            if room_type_id is not None:
                update_fields.append("otasync_room_type_id = ?")
                values.append(room_type_id)

            if enabled is not None:
                update_fields.append("otasync_enabled = ?")
                values.append(1 if enabled else 0)

            if price_percent is not None:
                update_fields.append("price_percent = ?")
                values.append(price_percent)

            if not update_fields:
                return False

            values.append(hotel_id)
            sql = f"UPDATE {table_name} SET {', '.join(update_fields)} WHERE id = ?"

            cursor.execute(sql, values)
            return cursor.rowcount > 0
    
    def get_hotels_with_otasync_enabled(self) -> List[Dict]:
        """Get all hotels that have OTASync integration enabled"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, url, city, country, otasync_property_id, otasync_room_type_id, otasync_enabled
                FROM hotels 
                WHERE otasync_enabled = 1 AND otasync_property_id IS NOT NULL AND otasync_room_type_id IS NOT NULL
                ORDER BY name
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_hotel_otasync_info(self, hotel_id: int) -> Optional[Dict]:
        """Get OTASync information for a specific hotel"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            # Prefer Django table
            if 'hotels_hotel' in tables:
                cursor.execute("""
                    SELECT name, otasync_property_id, otasync_room_type_id, otasync_enabled, price_percent
                    FROM hotels_hotel
                    WHERE id = ?
                """, (hotel_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'name': row['name'],
                        'otasync_property_id': row['otasync_property_id'],
                        'otasync_room_type_id': row['otasync_room_type_id'],
                        'otasync_enabled': bool(row['otasync_enabled']),
                        'price_percent': float(row['price_percent'] or 0.0)
                    }

            # Fallback to legacy table
            if 'hotels' in tables:
                cursor.execute("""
                    SELECT name, otasync_property_id, otasync_room_type_id, otasync_enabled, price_percent
                    FROM hotels
                    WHERE id = ?
                """, (hotel_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'name': row['name'],
                        'otasync_property_id': row['otasync_property_id'],
                        'otasync_room_type_id': row['otasync_room_type_id'],
                        'otasync_enabled': bool(row['otasync_enabled']),
                        'price_percent': float(row['price_percent'] or 0.0)
                    }

            return None

    def get_hotel_by_id(self, hotel_id: int) -> Optional[Dict]:
        """Get hotel by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM hotels WHERE id = ?", (hotel_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_hotel(self, hotel_id: int, data: Dict) -> bool:
        """Update hotel information"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build dynamic update query
                update_fields = []
                values = []
                
                allowed_fields = ['name', 'url', 'city', 'state', 'address', 'country', 'otasync_enabled', 'otasync_property_id', 'otasync_room_type_id', 'price_percent']
                for field in allowed_fields:
                    if field in data:
                        update_fields.append(f"{field} = ?")
                        values.append(data[field])
                
                if not update_fields:
                    return False
                
                # Add hotel_id for WHERE clause
                values.append(hotel_id)
                
                sql = f"UPDATE hotels SET {', '.join(update_fields)} WHERE id = ?"
                cursor.execute(sql, values)
                
                return cursor.rowcount > 0
        except Exception as e:
            log.error(f"Error updating hotel {hotel_id}: {e}")
            return False

    def delete_hotel(self, hotel_id: int) -> bool:
        """Delete hotel and all related scrapes"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Delete related scrapes first
                cursor.execute("DELETE FROM scrapes WHERE hotel_id_fk = ?", (hotel_id,))
                
                # Delete hotel
                cursor.execute("DELETE FROM hotels WHERE id = ?", (hotel_id,))
                
                return cursor.rowcount > 0
        except Exception as e:
            log.error(f"Error deleting hotel {hotel_id}: {e}")
            return False

    def get_average_price(self) -> float:
        """Get average price from recent scrapes"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT AVG(price_amount) as avg_price 
                    FROM scrapes 
                    WHERE price_amount IS NOT NULL 
                      AND price_amount > 0 
                      AND scraped_at >= datetime('now', '-30 days')
                """)
                row = cursor.fetchone()
                return float(row['avg_price'] or 0.0)
        except Exception as e:
            log.error(f"Error getting average price: {e}")
            return 0.0

    def get_last_scrape_date(self) -> Optional[str]:
        """Get the date of the last scrape"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(scraped_at) as last_scrape FROM scrapes")
                row = cursor.fetchone()
                return row['last_scrape'] if row else None
        except Exception as e:
            log.error(f"Error getting last scrape date: {e}")
            return None
