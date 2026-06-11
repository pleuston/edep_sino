// M11 navigation pass: Map as the front door, Sites as a section,
// the editor reachable from menu and document toolbar.

describe('Site navigation', () => {
  it('puts Map first and groups the registers', () => {
    cy.visit('/browse.html')
    cy.get('nav.menubar ul li a[href$="map.html"]', { timeout: 20000 }).should('exist')
    // Map is the first labeled item after the logo
    cy.get('nav.menubar > ul > li').eq(1).find('a')
      .should('have.attr', 'href')
      .and('include', 'map.html')
    // registers dropdown holds the three authority lists
    cy.get('nav.menubar details.dropdown').first().within(() => {
      cy.get('a[href$="/people"]').should('exist')
      cy.get('a[href$="/places"]').should('exist')
      cy.get('a[href$="/bibliography"]').should('exist')
    })
  })

  it('map page shows clustered sites and opens the site panel', () => {
    cy.visit('/map.html')
    cy.get('#sites-map .leaflet-container, #sites-map.leaflet-container', { timeout: 30000 })
      .should('exist')
    // a site marker with holdings renders and the panel auto-opens on it
    cy.get('#site-panel h2', { timeout: 30000 }).should('contain.text', '雲峰山')
    cy.get('#site-panel .site-inscriptions a')
      .first()
      .should('have.attr', 'href')
      .and('include', 'demo-zaoxiangji.xml')
    cy.get('#site-panel .site-meta a')
      .should('have.attr', 'href')
      .and('include', '/places/place-yunfengshan')
    cy.screenshot('map-page', { capture: 'viewport', overwrite: true })
  })

  it('sites index sorts by holdings', () => {
    cy.visit('/sites.html')
    cy.get('.sites-index .site-card', { timeout: 20000 })
      .should('have.length.greaterThan', 1)
    cy.get('.sites-index .site-card').first().within(() => {
      cy.get('.count').should('contain.text', '1')
      cy.get('.names').should('contain.text', '雲峰山')
      cy.get('.links a').first()
        .should('have.attr', 'href')
        .and('include', '/places/place-yunfengshan')
    })
  })

  it('reaches the editor from menu and document toolbar when logged in', () => {
    cy.login()
    // gated New entry in the menubar
    cy.visit('/browse.html')
    cy.get('nav.menubar pb-restricted a.menu-new', { timeout: 20000 })
      .should('have.attr', 'href')
      .and('include', 'edit.html')
    // Edit pencil on the document view
    cy.visit('/demo-zaoxiangji.xml')
    cy.get('nav.toolbar pb-restricted a[href*="edit.html"]', { timeout: 20000 })
      .should('have.attr', 'href')
      .and('include', 'id=demo-zaoxiangji')
      .and('include', 'collection=workspace')
  })
})
