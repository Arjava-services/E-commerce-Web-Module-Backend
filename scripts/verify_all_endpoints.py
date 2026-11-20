import os
import sys
import json
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

def print_section(title):
    print("\n" + "=" * 80)
    print(f"👉 {title}")
    print("=" * 80)

def verify():
    client = TestClient(app)
    
    # -------------------------------------------------------------------------
    # 1. GET /api/categories
    # -------------------------------------------------------------------------
    print_section("1. GET /api/categories")
    res1 = client.get("/api/categories")
    print(f"Status Code: {res1.status_code}")
    data1 = res1.json()
    assert res1.status_code == 200 and data1["success"] is True
    print(f"Found {len(data1['data'])} categories. Sample:")
    print(json.dumps(data1["data"][0], indent=2))
    sample_cat_id = data1["data"][0]["id"]
    sample_cat_slug = data1["data"][0]["slug"]

    # -------------------------------------------------------------------------
    # 2. POST /api/modules (Upload / Publish Dummy Module)
    # -------------------------------------------------------------------------
    print_section("2. POST /api/modules (Upload / Publish)")
    dummy_slug = f"interactive-checkout-modal-{int(time.time())}"
    dummy_payload = {
        "name": "Interactive Checkout Modal",
        "slug": dummy_slug,
        "categoryId": sample_cat_id,
        "shortDescription": "Animated responsive checkout modal with credit card and one-click pay.",
        "description": "# Interactive Checkout Modal\n\nA full-featured checkout modal component supporting credit card, PayPal, and Apple Pay.",
        "framework": "React",
        "language": "TypeScript",
        "version": "1.0.0",
        "tags": ["checkout", "payment", "modal", "react"],
        "files": [
            {
                "fileName": "CheckoutModal.tsx",
                "filePath": "src/components/CheckoutModal.tsx",
                "content": "import React from 'react';\n\nexport const CheckoutModal = ({ isOpen, onClose, total }: any) => {\n  if (!isOpen) return null;\n  return (\n    <div className='fixed inset-0 z-50 flex items-center justify-center bg-black/50'>\n      <div className='bg-white p-6 rounded-xl w-full max-w-lg'>\n        <h2 className='text-xl font-bold'>Order Summary: ${total}</h2>\n        <button onClick={onClose} className='mt-4 px-4 py-2 bg-indigo-600 text-white rounded'>Pay Now</button>\n      </div>\n    </div>\n  );\n};",
                "language": "typescript",
                "isEntry": True
            },
            {
                "fileName": "types.ts",
                "filePath": "src/types.ts",
                "content": "export interface CheckoutModalProps {\n  isOpen: boolean;\n  onClose: () => void;\n  total: number;\n}",
                "language": "typescript",
                "isEntry": False
            }
        ],
        "overview": "Lightweight, accessible checkout modal component.",
        "installation": f"npm install @company/{dummy_slug}",
        "apiReference": "import { CheckoutModal } from '@company/checkout-modal';",
        "integrationExample": "<CheckoutModal isOpen={isOpen} onClose={() => setIsOpen(false)} total={99.99} />"
    }
    res2 = client.post("/api/modules", json=dummy_payload)
    print(f"Status Code: {res2.status_code}")
    data2 = res2.json()
    assert res2.status_code == 201 and data2["success"] is True
    print(json.dumps(data2, indent=2))

    # -------------------------------------------------------------------------
    # 3. GET /api/modules (Catalog Search, Filter, Sort & Pagination)
    # -------------------------------------------------------------------------
    print_section("3. GET /api/modules?page=1&limit=4&sort=updated")
    res3 = client.get(f"/api/modules?page=1&limit=4&sort=updated&category={sample_cat_slug}")
    print(f"Status Code: {res3.status_code}")
    data3 = res3.json()
    assert res3.status_code == 200 and data3["success"] is True
    print(f"Total: {data3['data']['total']}, Page: {data3['data']['page']}, Total Pages: {data3['data']['totalPages']}, Limit: {data3['data']['limit']}")
    print(f"First item summary:")
    print(json.dumps(data3["data"]["items"][0], indent=2))

    # -------------------------------------------------------------------------
    # 4. GET /api/modules/:slug (Detail Page)
    # -------------------------------------------------------------------------
    print_section(f"4. GET /api/modules/{dummy_slug}")
    res4 = client.get(f"/api/modules/{dummy_slug}")
    print(f"Status Code: {res4.status_code}")
    data4 = res4.json()
    assert res4.status_code == 200 and data4["success"] is True
    print("Module details preview:")
    preview = {
        "id": data4["data"]["id"],
        "slug": data4["data"]["slug"],
        "name": data4["data"]["name"],
        "framework": data4["data"]["framework"],
        "language": data4["data"]["language"],
        "category": data4["data"]["category"],
        "tags": data4["data"]["tags"],
        "currentVersion": {
            "version": data4["data"]["currentVersion"]["version"],
            "files_count": len(data4["data"]["currentVersion"]["files"]),
            "entry_file": data4["data"]["currentVersion"]["files"][0]["fileName"]
        },
        "documentation": data4["data"]["documentation"]
    }
    print(json.dumps(preview, indent=2))

    # -------------------------------------------------------------------------
    # 5. GET /api/modules/:slug/versions/:version/files
    # -------------------------------------------------------------------------
    print_section(f"5. GET /api/modules/{dummy_slug}/versions/1.0.0/files")
    res5 = client.get(f"/api/modules/{dummy_slug}/versions/1.0.0/files")
    print(f"Status Code: {res5.status_code}")
    data5 = res5.json()
    assert res5.status_code == 200 and data5["success"] is True
    print(f"Retrieved {len(data5['data'])} files:")
    for f in data5["data"]:
        print(f"  - {f['filePath']} ({f['language']}) [isEntry={f['isEntry']}]")

    # -------------------------------------------------------------------------
    # 6. GET /api/modules/:slug/versions/:version/download (ZIP Stream)
    # -------------------------------------------------------------------------
    print_section(f"6. GET /api/modules/{dummy_slug}/versions/1.0.0/download")
    res6 = client.get(f"/api/modules/{dummy_slug}/versions/1.0.0/download")
    print(f"Status Code: {res6.status_code}")
    print(f"Content-Type: {res6.headers.get('content-type')}")
    print(f"Content-Disposition: {res6.headers.get('content-disposition')}")
    print(f"ZIP binary size: {len(res6.content)} bytes")
    assert res6.status_code == 200 and res6.headers.get("content-type") == "application/zip"

    # Check download count incremented
    after_dl_res = client.get(f"/api/modules/{dummy_slug}")
    dl_count = after_dl_res.json()["data"]["downloadCount"]
    print(f"Download count after download: {dl_count} (Incremented successfully!)")
    assert dl_count == 1

    # -------------------------------------------------------------------------
    # 7. GET /api/modules/stats
    # -------------------------------------------------------------------------
    print_section("7. GET /api/modules/stats")
    res7 = client.get("/api/modules/stats")
    print(f"Status Code: {res7.status_code}")
    data7 = res7.json()
    assert res7.status_code == 200 and data7["success"] is True
    print(json.dumps(data7, indent=2))

    # -------------------------------------------------------------------------
    # 8. GET /api/modules/featured
    # -------------------------------------------------------------------------
    print_section("8. GET /api/modules/featured")
    res8 = client.get("/api/modules/featured")
    print(f"Status Code: {res8.status_code}")
    data8 = res8.json()
    assert res8.status_code == 200 and data8["success"] is True
    print(f"Featured modules count: {len(data8['data'])}")
    if data8["data"]:
        print("First featured module:")
        print(json.dumps({
            "name": data8["data"][0]["name"],
            "slug": data8["data"][0]["slug"],
            "framework": data8["data"][0]["framework"],
            "downloadCount": data8["data"][0]["downloadCount"],
            "category": data8["data"][0]["category"],
            "tags": data8["data"][0]["tags"]
        }, indent=2))

    print("\n" + "=" * 80)
    print("🎉 ALL 8 API CALLS EXECUTED PERFECTLY WITH ZERO ISSUES!")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    verify()
