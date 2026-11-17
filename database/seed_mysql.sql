-- ============================================================================
-- Seed Data for MySQL 8.0+
-- ============================================================================

INSERT INTO categories (id, slug, name, description, icon, `displayOrder`) VALUES
(UUID(), 'authentication-accounts', 'Authentication & Accounts', 'User login, registration, session management, and profile controls.', 'Lock', 1),
(UUID(), 'product-catalogue', 'Product Catalogue', 'Display items, rich galleries, filters, and product detail components.', 'Package', 2),
(UUID(), 'cart-checkout', 'Cart & Checkout', 'Slide-over shopping cart, multi-step checkout, and order summary.', 'ShoppingCart', 3),
(UUID(), 'payments-billing', 'Payments & Billing', 'Stripe, PayPal, credit card forms, and tax computation modules.', 'CreditCard', 4),
(UUID(), 'orders-fulfillment', 'Orders & Fulfillment', 'Order tracking, dispatch history, invoice generator, and statuses.', 'Truck', 5),
(UUID(), 'search-filtering', 'Search & Filtering', 'Faceted search, instant auto-complete bar, and category filters.', 'Search', 6),
(UUID(), 'reviews-ratings', 'Reviews & Ratings', 'Star ratings, verified buyer review list, and rating submission.', 'Star', 7)
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  description = VALUES(description),
  icon = VALUES(icon),
  `displayOrder` = VALUES(`displayOrder`);

INSERT INTO tags (id, slug, name) VALUES
(UUID(), 'react', 'React'),
(UUID(), 'typescript', 'TypeScript'),
(UUID(), 'cart', 'Cart'),
(UUID(), 'ui-component', 'UI Component'),
(UUID(), 'tailwind', 'Tailwind CSS'),
(UUID(), 'checkout', 'Checkout')
ON DUPLICATE KEY UPDATE name = VALUES(name);
