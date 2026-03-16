-- Business types (Фулфілмент, Юрист, Клініка...)
CREATE TABLE IF NOT EXISTS business_types (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  slug text UNIQUE NOT NULL,
  icon text DEFAULT '📦',
  created_at timestamptz DEFAULT now()
);

-- Niche tree (двохрівнева ієрархія)
CREATE TABLE IF NOT EXISTS niches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_type_id uuid REFERENCES business_types(id) ON DELETE CASCADE,
  parent_id uuid REFERENCES niches(id) ON DELETE CASCADE,
  name text NOT NULL,
  slug text NOT NULL,
  icon text DEFAULT '📁',
  search_queries jsonb DEFAULT '[]',
  is_active boolean DEFAULT true,
  sort_order int DEFAULT 0,
  created_at timestamptz DEFAULT now()
);

-- User settings
CREATE TABLE IF NOT EXISTS user_settings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  business_type_id uuid REFERENCES business_types(id),
  selected_niches jsonb DEFAULT '[]',
  ai_model text DEFAULT 'gemini-2.0-flash',
  email_tone text DEFAULT 'friendly',
  language text DEFAULT 'uk',
  sender_name text DEFAULT 'MTP Fulfillment',
  sender_email text DEFAULT '',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Seed data
INSERT INTO business_types (name, slug, icon) VALUES
  ('Фулфілмент', 'fulfillment', '📦'),
  ('Юридичні послуги', 'legal', '⚖️'),
  ('Медична клініка', 'medical', '🏥'),
  ('IT компанія', 'it', '💻'),
  ('Маркетингове агентство', 'marketing', '📣')
ON CONFLICT (slug) DO NOTHING;

-- Fulfillment niches
WITH bt AS (SELECT id FROM business_types WHERE slug = 'fulfillment')
INSERT INTO niches (business_type_id, name, slug, icon, search_queries, sort_order)
SELECT bt.id, n.name, n.slug, n.icon, n.queries::jsonb, n.sort
FROM bt, (VALUES
  ('Косметика та краса', 'cosmetics', '💄', '["косметика інтернет-магазин", "beauty shop Ukraine", "cosmetics store Ukraine"]', 1),
  ('Дитячі іграшки', 'toys', '🧸', '["іграшки дитячі інтернет-магазин", "toys shop Ukraine", "дитячі товари онлайн"]', 2),
  ('Одяг та взуття', 'fashion', '👗', '["одяг інтернет-магазин", "fashion shop Ukraine", "взуття онлайн"]', 3),
  ('Електроніка', 'electronics', '📱', '["електроніка інтернет-магазин", "electronics shop Ukraine"]', 4),
  ('Меблі та декор', 'furniture', '🛋️', '["меблі інтернет-магазин", "furniture shop Ukraine"]', 5),
  ('Спорт та туризм', 'sports', '⚽', '["спортивні товари", "sports shop Ukraine"]', 6),
  ('Зоотовари', 'pets', '🐾', '["зоотовари інтернет-магазин", "pet shop Ukraine"]', 7),
  ('Їжа та напої', 'food', '🍕', '["їжа доставка онлайн", "food delivery Ukraine"]', 8),
  ('Ювелірні прикраси', 'jewelry', '💍', '["ювелірні прикраси інтернет-магазин", "jewelry shop Ukraine"]', 9),
  ('Товари для дому', 'home', '🏠', '["товари для дому", "home goods Ukraine"]', 10)
) AS n(name, slug, icon, queries, sort)
ON CONFLICT DO NOTHING;

-- Calendly URL setting
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS calendly_url text DEFAULT 'https://calendly.com/mtpgrouppromo/30min';
