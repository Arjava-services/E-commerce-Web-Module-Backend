import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import app from '../src/app.js';
import { pool } from '../src/config/db.js';

async function runTests() {
  console.log('🧪 Starting API Verification Tests...\n');

  // Start temporary test server on an ephemeral port
  const server = createServer(app);
  await new Promise<void>((resolve) => server.listen(0, resolve));
  const address = server.address() as any;
  const baseUrl = `http://127.0.0.1:${address.port}/api`;

  try {
    // -------------------------------------------------------------
    // 1. GET /api/categories
    // -------------------------------------------------------------
    console.log('1️⃣ Testing GET /api/categories...');
    const catRes = await fetch(`${baseUrl}/categories`);
    assert.equal(catRes.status, 200);
    const catJson = await catRes.json();
    assert.equal(catJson.success, true);
    assert.ok(Array.isArray(catJson.data), 'Categories data must be an array');
    assert.ok(catJson.data.length > 0, 'Should have at least 1 category');
    assert.ok(catJson.data[0].slug, 'Category must have a slug');
    assert.ok(catJson.data[0].name, 'Category must have a name');
    console.log(`   ✅ Success: Returned ${catJson.data.length} categories.`);

    // -------------------------------------------------------------
    // 2. GET /api/modules/stats
    // -------------------------------------------------------------
    console.log('2️⃣ Testing GET /api/modules/stats...');
    const statsRes = await fetch(`${baseUrl}/modules/stats`);
    assert.equal(statsRes.status, 200);
    const statsJson = await statsRes.json();
    assert.equal(statsJson.success, true);
    assert.ok(typeof statsJson.data.publishedModules === 'number', 'publishedModules must be number');
    assert.ok(typeof statsJson.data.totalDownloads === 'number', 'totalDownloads must be number');
    console.log(`   ✅ Success: ${statsJson.data.publishedModules} published modules, ${statsJson.data.totalDownloads} downloads.`);

    // -------------------------------------------------------------
    // 3. GET /api/modules (with query params)
    // -------------------------------------------------------------
    console.log('3️⃣ Testing GET /api/modules (pagination & filters)...');
    const modulesRes = await fetch(`${baseUrl}/modules?page=1&limit=6&sort=updated`);
    assert.equal(modulesRes.status, 200);
    const modulesJson = await modulesRes.json();
    assert.equal(modulesJson.success, true);
    assert.ok(Array.isArray(modulesJson.data.items), 'items must be an array');
    assert.ok(typeof modulesJson.data.total === 'number', 'total must be a number');
    assert.equal(modulesJson.data.page, 1);
    console.log(`   ✅ Success: Returned page 1 with ${modulesJson.data.items.length} items out of ${modulesJson.data.total} total.`);

    // -------------------------------------------------------------
    // 4. POST /api/modules (Upload / Publish)
    // -------------------------------------------------------------
    console.log('4️⃣ Testing POST /api/modules (Upload / Publish)...');
    const testSlug = `e2e-test-module-${Date.now()}`;
    const uploadPayload = {
      name: 'E2E Test Button Module',
      slug: testSlug,
      categoryId: catJson.data[0].id,
      shortDescription: 'High quality animated interactive button for e-commerce checkouts.',
      description: 'Extensive detailed description of the interactive button component.',
      framework: 'React',
      language: 'TypeScript',
      version: '1.0.0',
      tags: ['react', 'button', 'interactive'],
      files: [
        {
          fileName: 'Button.tsx',
          filePath: 'src/Button.tsx',
          content: 'export function Button() { return <button className="btn">Checkout</button>; }',
          language: 'typescript',
          isEntry: true,
        },
        {
          fileName: 'Button.css',
          filePath: 'src/Button.css',
          content: '.btn { background-color: #6366f1; color: white; border-radius: 8px; }',
          language: 'css',
          isEntry: false,
        },
      ],
    };

    const uploadRes = await fetch(`${baseUrl}/modules`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(uploadPayload),
    });
    assert.equal(uploadRes.status, 201);
    const uploadJson = await uploadRes.json();
    assert.equal(uploadJson.success, true);
    assert.equal(uploadJson.data.slug, testSlug);
    assert.ok(uploadJson.data.id, 'Must return created module id');
    console.log(`   ✅ Success: Published module with slug "${uploadJson.data.slug}" (id: ${uploadJson.data.id}).`);

    // -------------------------------------------------------------
    // 5. GET /api/modules/:slug
    // -------------------------------------------------------------
    console.log(`5️⃣ Testing GET /api/modules/${testSlug}...`);
    const detailRes = await fetch(`${baseUrl}/modules/${testSlug}`);
    assert.equal(detailRes.status, 200);
    const detailJson = await detailRes.json();
    assert.equal(detailJson.success, true);
    assert.equal(detailJson.data.slug, testSlug);
    assert.ok(detailJson.data.currentVersion, 'Must include currentVersion');
    assert.equal(detailJson.data.currentVersion.version, '1.0.0');
    assert.equal(detailJson.data.currentVersion.files.length, 2, 'Must contain 2 files');
    assert.equal(detailJson.data.currentVersion.files[0].fileName, 'Button.tsx');
    console.log(`   ✅ Success: Module detail contains currentVersion with ${detailJson.data.currentVersion.files.length} source code files.`);

    // -------------------------------------------------------------
    // 6. GET /api/modules/:slug/versions/:version/download
    // -------------------------------------------------------------
    console.log(`6️⃣ Testing GET /api/modules/${testSlug}/versions/1.0.0/download...`);
    const dlRes = await fetch(`${baseUrl}/modules/${testSlug}/versions/1.0.0/download`);
    assert.equal(dlRes.status, 200);
    assert.equal(dlRes.headers.get('content-type'), 'application/zip');
    assert.ok(dlRes.headers.get('content-disposition')?.includes('attachment;'));
    const zipBytes = await dlRes.arrayBuffer();
    assert.ok(zipBytes.byteLength > 50, 'ZIP payload must have valid non-empty byte stream');
    console.log(`   ✅ Success: Received ${zipBytes.byteLength} bytes valid ZIP package.`);

    // Verify download count increment
    const afterDlRes = await fetch(`${baseUrl}/modules/${testSlug}`);
    const afterDlJson = await afterDlRes.json();
    assert.equal(afterDlJson.data.downloadCount, 1, 'Download count should have incremented to 1');
    console.log('   ✅ Success: Module download count incremented properly.');

    console.log('\n🎉 ALL 6 API ENDPOINTS PASSED VERIFICATION PERFECTLY!\n');
  } finally {
    server.close();
    await pool.end();
  }
}

runTests().catch((err) => {
  console.error('\n❌ Test execution failed:', err);
  process.exit(1);
});

