# kakebe_apps/categories/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, TagViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'tags', TagViewSet, basename='tag')

urlpatterns = [
    path('', include(router.urls)),
]

"""
========================================
AVAILABLE API ENDPOINTS
========================================

CATEGORIES:
-----------

1. List all categories (paginated)
   GET /api/categories/
   GET /api/categories/?page=1&page_size=20
   GET /api/categories/?search=electronics
   GET /api/categories/?ordering=name
   GET /api/categories/?ordering=-sort_order
   GET /api/categories/?top_level=true
   GET /api/categories/?featured=true
   GET /api/categories/?parent_id=<uuid>

2. Get featured parent categories (not paginated)
   GET /api/categories/featured/

3. Get all parent categories (paginated)
   GET /api/categories/parents/
   GET /api/categories/parents/?page=1&page_size=10

4. Get complete category tree (hierarchical, not paginated)
   GET /api/categories/tree/

5. Get single category details (with children and breadcrumbs)
   GET /api/categories/<slug>/
   GET /api/categories/electronics/
   GET /api/categories/smartphones/

6. Get subcategories of a category (paginated)
   GET /api/categories/<slug>/subcategories/
   GET /api/categories/electronics/subcategories/
   GET /api/categories/electronics/subcategories/?page=1&page_size=10
   GET /api/categories/electronics/subcategories/?search=phone


TAGS:
-----

1. List all tags (paginated)
   GET /api/tags/
   GET /api/tags/?page=1&page_size=20
   GET /api/tags/?search=tech

2. Get single tag details
   GET /api/tags/<slug>/
   GET /api/tags/trending/


========================================
QUERY PARAMETERS
========================================

Pagination:
-----------
- page: Page number (default: 1)
- page_size: Items per page (default: 20, max: 100)
  Example: ?page=2&page_size=50

Search:
-------
- search: Search by name or description
  Example: ?search=electronics

Ordering:
---------
- ordering: Sort by field (prefix with - for descending)
  Available fields: name, sort_order, created_at
  Example: ?ordering=name
  Example: ?ordering=-created_at

Filtering:
----------
- parent_id: Filter by parent category UUID
  Example: ?parent_id=123e4567-e89b-12d3-a456-426614174000

- top_level: Show only parent categories (no parent)
  Example: ?top_level=true

- featured: Show only featured categories
  Example: ?featured=true


========================================
RESPONSE FORMATS
========================================

List Response (Paginated):
{
  "count": 45,
  "next": "http://example.com/api/categories/?page=2",
  "previous": null,
  "results": [...]
}

Category List Item:
{
  "id": "uuid",
  "name": "Electronics",
  "slug": "electronics",
  "icon": "icon-electronics",
  "description": "Electronic devices",
  "parent": null,
  "parent_name": null,
  "children_count": 5,
  "allows_order_intent": true,
  "allows_cart": true,
  "is_contact_only": false,
  "is_featured": true,
  "sort_order": 1,
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T00:00:00Z"
}

Category Detail:
{
  "id": "uuid",
  "name": "Smartphones",
  "slug": "smartphones",
  "parent": "parent-uuid",
  "parent_details": {
    "id": "parent-uuid",
    "name": "Electronics",
    "slug": "electronics"
  },
  "children": [...],
  "children_count": 3,
  "breadcrumbs": [
    {"id": "uuid", "name": "Electronics", "slug": "electronics"},
    {"id": "uuid", "name": "Smartphones", "slug": "smartphones"}
  ],
  ...
}

Category Tree:
{
  "id": "uuid",
  "name": "Electronics",
  "slug": "electronics",
  "children": [
    {
      "id": "uuid",
      "name": "Smartphones",
      "children": [...]
    }
  ]
}


========================================
USAGE EXAMPLES
========================================

JavaScript/Fetch:
-----------------
// Get featured categories
fetch('/api/categories/featured/')
  .then(res => res.json())
  .then(data => console.log(data));

// Get paginated categories with search
fetch('/api/categories/?page=1&page_size=10&search=phone')
  .then(res => res.json())
  .then(data => {
    console.log('Total:', data.count);
    console.log('Results:', data.results);
  });

// Get category details
fetch('/api/categories/electronics/')
  .then(res => res.json())
  .then(category => {
    console.log('Breadcrumbs:', category.breadcrumbs);
    console.log('Children:', category.children);
  });

// Get subcategories
fetch('/api/categories/electronics/subcategories/?page=1')
  .then(res => res.json())
  .then(data => console.log(data.results));


Python/Requests:
----------------
import requests

# Get featured categories
response = requests.get('http://localhost:8000/api/categories/featured/')
featured = response.json()

# Get paginated list
response = requests.get('http://localhost:8000/api/categories/', params={
    'page': 1,
    'page_size': 20,
    'search': 'electronics',
    'ordering': 'name'
})
categories = response.json()

# Get category tree
response = requests.get('http://localhost:8000/api/categories/tree/')
tree = response.json()


cURL:
-----
# Get featured categories
curl -X GET "http://localhost:8000/api/categories/featured/"

# Get paginated with filters
curl -X GET "http://localhost:8000/api/categories/?page=1&page_size=10&featured=true"

# Get category details
curl -X GET "http://localhost:8000/api/categories/electronics/"

# Get subcategories
curl -X GET "http://localhost:8000/api/categories/electronics/subcategories/"


========================================
FRONTEND IMPLEMENTATION TIPS
========================================

1. Homepage Featured Categories:
   - Use: GET /api/categories/featured/
   - Cache: 1 hour (featured categories change rarely)

2. Navigation Menu:
   - Use: GET /api/categories/tree/
   - Cache: 30 minutes
   - Limit depth to 2-3 levels for better UX

3. Category Listing Page:
   - Use: GET /api/categories/?top_level=true
   - Implement pagination
   - Add search functionality

4. Category Details Page:
   - Use: GET /api/categories/{slug}/
   - Show breadcrumbs for navigation
   - Display children as grid/list

5. Subcategory Listing:
   - Use: GET /api/categories/{slug}/subcategories/
   - Implement pagination
   - Add sorting options

6. Search Results:
   - Use: GET /api/categories/?search=query
   - Implement debouncing (300ms delay)
   - Show loading states

========================================
"""