# Professional UI Standards

## Design Principles

Build a dashboard that is:
- **Corporate**: Professional, trustworthy appearance
- **Accessible**: Readable by all users including color-blind
- **Responsive**: Works on desktop, tablet, mobile
- **Clear**: Users understand data at a glance
- **Fast**: Minimal loading, smooth interactions

## Color Palette (Light Corporate Theme)

Use these colors consistently across the application:

```
Primary (Trust/Security):
  - Primary: #1F4788 (dark blue)
  - Light: #E8EFF5 (very light blue)

Status/Alerts:
  - Critical Risk: #D32F2F (red)
  - Warning: #F57C00 (orange)
  - Normal: #388E3C (green)
  - Neutral: #616161 (gray)

Backgrounds:
  - Page: #FFFFFF (white)
  - Section: #F5F5F5 (light gray)
  - Hover: #E8EFF5 (light blue hover)

Text:
  - Primary text: #212121 (very dark gray)
  - Secondary text: #757575 (medium gray)
  - Disabled: #BDBDBD (light gray)

Accents:
  - Link: #1976D2 (medium blue)
  - Border: #E0E0E0 (light border)
```

## Layout Structure

```
┌─────────────────────────────────────────────┐
│         PROJECT ANALYTICS (header)          │  ← Moving line animation
├─────────────────────────────────────────────┤
│  Filters (Warehouse, Medicine Type)         │
├─────────────────────────────────────────────┤
│ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│ │   KPI #1   │ │   KPI #2   │ │  KPI #3  │ │  ← 3 main KPIs
│ └────────────┘ └────────────┘ └──────────┘ │
├─────────────────────────────────────────────┤
│                                             │
│         Main Chart / Table Area             │  ← Primary data view
│                                             │
├─────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────┐ │
│ │         Secondary Chart                 │ │  ← Supporting visualization
│ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

## KPI Cards

KPI cards display key metrics with clear visual hierarchy:

```
┌─────────────────────┐
│ [Icon] Label        │
│                     │
│ Large Number        │  Bold, readable
│ (e.g., "45")        │
│                     │
│ Subtitle            │  Secondary text
│ (e.g., "Critical")  │
└─────────────────────┘
```

### Card Guidelines
- **Size**: Fixed width (200-250px), fixed height (100-120px)
- **Font size**: Main number 32-40pt, label 12-14pt
- **Color coding**: Card background reflects status
  - Red background for CRITICAL RISK
  - Orange for WARNINGS
  - Green for NORMAL
  - Gray for INFO
- **Content**: One metric per card (no clutter)
- **Padding**: 16px minimum around content

### Example KPI Set
1. **Total Critical Medicines** (count of critical-risk items)
2. **Expired Stock** (count of expired items)
3. **Expiring Soon** (count of medicines expiring within 30 days)
4. **Low Stock Alerts** (count of below-reorder items)

## Responsive Layout

| Screen Size | Layout |
|-------------|--------|
| Desktop (>1200px) | 3-column KPI cards, full-width charts |
| Tablet (768-1200px) | 2-column KPI cards, stacked charts |
| Mobile (<768px) | 1-column KPI cards, single chart per view |

## Filters

Provide clean, discoverable filters:

```
┌─ Filters (collapsible on mobile) ─────────┐
│ Warehouse: [Dropdown v]                   │
│ Status: [Multi-select ▼]                  │
│ Date Range: [From] [To]                   │
│ [Reset]  [Apply]                          │
└───────────────────────────────────────────┘
```

### Filter Rules
- Dropdowns for categorical data (warehouse, medicine type)
- Multi-select for multiple statuses (expired, expiring, low stock)
- Date pickers for date ranges
- Reset button to clear all filters
- Apply button (or auto-apply with 300ms debounce)

## Charts & Visualizations

### Chart Types Allowed
- **Plotly bar charts**: Stock levels, inventory by warehouse
- **Plotly line charts**: Trend analysis over time
- **Plotly pie charts**: Status distribution (use sparingly)
- **Tables**: Detailed medicine list with sorting

### Chart Rules
- No more than 5-7 colors per chart
- Always include a legend
- Axes labeled clearly with units
- Hover tooltips show full values
- Responsive: single column on mobile
- No 3D effects or excessive animations

### Color Application
- Use the status palette (red for critical, orange for warning, etc.)
- Ensure adequate contrast (WCAG AA minimum)
- Don't rely on color alone to convey information (add labels/legend)

## Header

A professional header with moving accent line:

```
┌────────────────────────────────────┐
│  PROJECT ANALYTICS                 │
│  ▓▓▓▓▓▓▓▓▓─────────────────────    │ ← Animated line (moves left-right)
└────────────────────────────────────┘
```

### Rules
- Font: Bold, 24-28pt, primary color (#1F4788)
- Accent line: Primary color, moves continuously (3-5 sec cycle)
- Padding: 20px top/bottom, 24px left/right
- Height: 80-100px
- Always visible (sticky if scrolling)

## Error & Empty States

Provide clear feedback when things go wrong or are empty:

```
Empty State:
┌─────────────────────────────┐
│         📦                  │
│  No data available          │
│  Try adjusting filters      │
└─────────────────────────────┘

Error State:
┌─────────────────────────────┐
│         ⚠️                   │
│  Something went wrong       │
│  Please try again           │
└─────────────────────────────┘
```

### Error Guidelines
- Clear, user-friendly error message
- Suggest corrective action
- No technical jargon or stack traces
- Icon + text combination

## Animations & Interactions

**Allowed animations:**
- ✓ Hover states on cards (opacity change, slight scale)
- ✓ Smooth transitions on filter changes (300ms)
- ✓ Moving header accent line (continuous)
- ✓ Loading spinner (subtle, centered)

**Avoid:**
- ✗ Bouncing or spinning animations
- ✗ Auto-playing video or looping GIFs
- ✗ Excessive fade-in effects on page load
- ✗ Parallax scrolling

## Accessibility Checklist

- [ ] Color contrast meets WCAG AA (4.5:1 for text)
- [ ] All interactive elements are keyboard-accessible
- [ ] Hover tooltips are available for all icons
- [ ] Form labels are associated with inputs
- [ ] Charts have alt text or table fallback
- [ ] No information conveyed by color alone
- [ ] Loading states are announced to screen readers
- [ ] Focus indicators are visible

## Implementation Rules

1. Use Streamlit's built-in components (st.columns, st.metric, st.plotly_chart)
2. No custom CSS unless absolutely necessary
3. Consistent spacing: multiples of 8px (8, 16, 24, 32)
4. Typography: 14px body, 16px labels, 24pt headers
5. Test on desktop, tablet, mobile before shipping
6. Validate all colors meet contrast requirements
7. Performance: dashboards should load in <3 seconds
