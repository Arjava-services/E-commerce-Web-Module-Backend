-- ============================================================================
-- Seed Data for E-Commerce Web Module Platform
-- ============================================================================

-- 1. Insert Categories
INSERT INTO categories (id, slug, name, description, icon, "displayOrder") VALUES
(gen_random_uuid()::text, 'authentication-accounts', 'Authentication & Accounts', 'User login, registration, session management, and profile controls.', 'Lock', 1),
(gen_random_uuid()::text, 'product-catalogue', 'Product Catalogue', 'Display items, rich galleries, filters, and product detail components.', 'Package', 2),
(gen_random_uuid()::text, 'cart-checkout', 'Cart & Checkout', 'Slide-over shopping cart, multi-step checkout, and order summary.', 'ShoppingCart', 3),
(gen_random_uuid()::text, 'payments-billing', 'Payments & Billing', 'Stripe, PayPal, credit card forms, and tax computation modules.', 'CreditCard', 4),
(gen_random_uuid()::text, 'orders-fulfillment', 'Orders & Fulfillment', 'Order tracking, dispatch history, invoice generator, and statuses.', 'Truck', 5),
(gen_random_uuid()::text, 'search-filtering', 'Search & Filtering', 'Faceted search, instant auto-complete bar, and category filters.', 'Search', 6),
(gen_random_uuid()::text, 'reviews-ratings', 'Reviews & Ratings', 'Star ratings, verified buyer review list, and rating submission.', 'Star', 7)
ON CONFLICT (slug) DO UPDATE SET
  name = EXCLUDED.name,
  description = EXCLUDED.description,
  icon = EXCLUDED.icon,
  "displayOrder" = EXCLUDED."displayOrder";

-- 2. Insert Sample Tags
INSERT INTO tags (id, slug, name) VALUES
(gen_random_uuid()::text, 'react', 'React'),
(gen_random_uuid()::text, 'typescript', 'TypeScript'),
(gen_random_uuid()::text, 'cart', 'Cart'),
(gen_random_uuid()::text, 'ui-component', 'UI Component'),
(gen_random_uuid()::text, 'tailwind', 'Tailwind CSS'),
(gen_random_uuid()::text, 'checkout', 'Checkout')
ON CONFLICT (slug) DO NOTHING;

-- 3. Insert Sample Module: Shopping Cart Drawer
INSERT INTO modules (id, slug, name, "shortDescription", description, "categoryId", status, framework, language, "downloadCount")
SELECT
  gen_random_uuid()::text,
  'shopping-cart-drawer',
  'Shopping Cart Drawer',
  'A slide-over cart drawer with quantity counters, coupon code box, and subtotal calculation.',
  'Full featured accessible drawer shopping cart built with React and Tailwind CSS. Supports live badge updates, item deletion, instant price calculation and checkout redirecting.',
  c.id,
  'PUBLISHED',
  'React',
  'TypeScript',
  450
FROM categories c
WHERE c.slug = 'cart-checkout'
ON CONFLICT (slug) DO UPDATE SET
  name = EXCLUDED.name,
  "shortDescription" = EXCLUDED."shortDescription",
  description = EXCLUDED.description,
  status = EXCLUDED.status,
  framework = EXCLUDED.framework,
  language = EXCLUDED.language;

-- 4. Version for Shopping Cart Drawer
INSERT INTO module_versions (id, "moduleId", version, changelog, "isLatest", status)
SELECT
  gen_random_uuid()::text,
  m.id,
  '1.0.0',
  'Initial stable release with cart drawer animation and quantity controls.',
  true,
  'PUBLISHED'
FROM modules m
WHERE m.slug = 'shopping-cart-drawer'
ON CONFLICT ("moduleId", version) DO UPDATE SET
  changelog = EXCLUDED.changelog,
  "isLatest" = EXCLUDED."isLatest",
  status = EXCLUDED.status;

-- 5. Files for Shopping Cart Drawer
DELETE FROM module_files WHERE "moduleVersionId" IN (
  SELECT v.id FROM module_versions v
  JOIN modules m ON v."moduleId" = m.id
  WHERE m.slug = 'shopping-cart-drawer' AND v.version = '1.0.0'
);

INSERT INTO module_files (id, "moduleVersionId", "filePath", "fileName", language, content, "isEntry")
SELECT
  gen_random_uuid()::text,
  v.id,
  'src/CartDrawer.tsx',
  'CartDrawer.tsx',
  'typescript',
  'import React from "react";

export interface CartItem {
  id: string;
  title: string;
  price: number;
  quantity: number;
  image?: string;
}

export interface CartDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  items: CartItem[];
  onUpdateQuantity: (id: string, delta: number) => void;
  onCheckout: () => void;
}

export const CartDrawer: React.FC<CartDrawerProps> = ({
  isOpen,
  onClose,
  items,
  onUpdateQuantity,
  onCheckout,
}) => {
  if (!isOpen) return null;

  const total = items.reduce((acc, item) => acc + item.price * item.quantity, 0);

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-md bg-white dark:bg-slate-900 h-full p-6 shadow-2xl flex flex-col">
        <div className="flex items-center justify-between border-b pb-4">
          <h2 className="text-xl font-bold">Shopping Cart ({items.length})</h2>
          <button onClick={onClose} className="p-2 text-slate-500 hover:text-slate-800">Close</button>
        </div>
        <div className="flex-1 overflow-y-auto py-4 space-y-4">
          {items.map((item) => (
            <div key={item.id} className="flex justify-between items-center border-b pb-2">
              <div>
                <p className="font-semibold">{item.title}</p>
                <p className="text-sm text-slate-500">${item.price.toFixed(2)}</p>
              </div>
              <div className="flex items-center space-x-2">
                <button onClick={() => onUpdateQuantity(item.id, -1)} className="px-2 py-1 bg-slate-100 rounded">-</button>
                <span>{item.quantity}</span>
                <button onClick={() => onUpdateQuantity(item.id, 1)} className="px-2 py-1 bg-slate-100 rounded">+</button>
              </div>
            </div>
          ))}
        </div>
        <div className="border-t pt-4">
          <div className="flex justify-between text-lg font-bold mb-4">
            <span>Subtotal:</span>
            <span>${total.toFixed(2)}</span>
          </div>
          <button onClick={onCheckout} className="w-full py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700">
            Proceed to Checkout
          </button>
        </div>
      </div>
    </div>
  );
};',
  true
FROM module_versions v
JOIN modules m ON v."moduleId" = m.id
WHERE m.slug = 'shopping-cart-drawer' AND v.version = '1.0.0';

INSERT INTO module_files (id, "moduleVersionId", "filePath", "fileName", language, content, "isEntry")
SELECT
  gen_random_uuid()::text,
  v.id,
  'src/types.ts',
  'types.ts',
  'typescript',
  'export interface CartItem {
  id: string;
  title: string;
  price: number;
  quantity: number;
  image?: string;
}',
  false
FROM module_versions v
JOIN modules m ON v."moduleId" = m.id
WHERE m.slug = 'shopping-cart-drawer' AND v.version = '1.0.0';

-- 6. Link Tags to Module
INSERT INTO module_tags ("moduleId", "tagId")
SELECT m.id, t.id
FROM modules m, tags t
WHERE m.slug = 'shopping-cart-drawer' AND t.slug IN ('react', 'typescript', 'cart', 'ui-component')
ON CONFLICT DO NOTHING;

