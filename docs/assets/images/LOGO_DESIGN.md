# AgentWeave Logo Design

## Visual Design

The AgentWeave logo (`logo.svg`) represents the core principles of the SDK:

### Design Elements

1. **Shield Shape**
   - Represents security and protection
   - Classic security iconography
   - Conveys trust and reliability

2. **Woven Mesh Pattern**
   - Horizontal and vertical weave lines
   - Represents agent-to-agent connections
   - Symbolizes the network of secure agents
   - "AgentWeave" concept visualized

3. **Connection Nodes**
   - Circles at mesh intersections
   - Represent individual AI agents
   - Central node has pulsing animation
   - Shows active agent communication

4. **Lock Icon**
   - Small lock embedded in shield top
   - Represents cryptographic security
   - SPIFFE/SPIRE identity system
   - Zero-trust security model

### Color Scheme

- **Primary Blue**: `#2563eb` (37, 99, 235)
  - Represents trust, security, professionalism
  - Used for shield outline and primary nodes

- **Secondary Purple**: `#7c3aed` (124, 58, 237)
  - Represents innovation and advanced technology
  - Used for gradients and accent nodes

- **Gradients**: Smooth transitions between blue and purple
  - Creates depth and modern aesthetic
  - Two gradient directions for visual interest

### Technical Specifications

- **File Format**: SVG (Scalable Vector Graphics)
- **Dimensions**: 200×200 viewBox (infinitely scalable)
- **File Size**: ~3.2 KB (optimized)
- **Animation**: Subtle pulse on central node (2s cycle)
- **Accessibility**: No text, purely visual icon

### Design Philosophy

**"Secure connections woven together"**

The logo visually communicates:
- ✅ Security-first approach (shield + lock)
- ✅ Interconnected agents (woven mesh)
- ✅ Active communication (pulsing center)
- ✅ Professional reliability (clean, simple design)
- ✅ Modern technology (gradients, animation)

### Usage Guidelines

#### ✅ Recommended Uses

- Documentation header
- GitHub repository
- Social media cards
- Presentation slides
- Marketing materials
- Product packaging

#### ❌ Not Recommended

- Do not stretch or distort
- Do not change colors arbitrarily
- Do not add effects or filters
- Do not use on busy backgrounds
- Do not make smaller than 32×32px

#### Background Colors

The logo works well on:
- ✅ White backgrounds
- ✅ Light gray backgrounds (#f5f5f5 or lighter)
- ✅ Dark backgrounds (#1a202c or darker)

May need adjustment for:
- ⚠️ Mid-tone backgrounds (consider outline version)
- ⚠️ Colored backgrounds (test contrast)

### Variations

The current logo is the **full color version**. Future variations could include:

1. **Monochrome**: Single color version for print
2. **White**: For dark backgrounds
3. **Simplified**: Without gradients for small sizes
4. **Wordmark**: Logo + "AgentWeave" text

These are not currently implemented but can be created from the base design.

### Animation Details

The central node includes a subtle animation:
- **Property**: Radius and opacity
- **Duration**: 2 seconds
- **Repeat**: Infinite loop
- **Effect**: Gentle pulsing (6px → 8px → 6px)
- **Purpose**: Suggests active agent communication

To disable animation (for static contexts):
- Remove the `<animate>` elements from the SVG
- Or use CSS: `svg * { animation: none !important; }`

### File Locations

- **Main Logo**: `/docs/assets/images/logo.svg`
- **Favicon Version**: `/docs/assets/favicon/favicon.svg` (simplified)

### Comparison: Logo vs Favicon

| Feature | Main Logo | Favicon |
|---------|-----------|---------|
| Size | 200×200 | 32×32 |
| Detail | High | Simplified |
| Animation | Yes (pulse) | No |
| Weave pattern | Curved, detailed | Straight, minimal |
| Lock icon | Detailed | Minimal |
| Best for | Headers, cards | Browser tabs |

## Design Credits

Created for the AgentWeave SDK Documentation project.

Design concept: Secure agent mesh with cryptographic identity.

Color palette chosen to align with modern SaaS and security product design trends.
