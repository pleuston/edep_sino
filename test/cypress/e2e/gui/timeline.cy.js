// M-J4: jinshi timeline (年表) — chronology page, mini-timelines, attestation strip.

describe('Jinshi timeline GUI', () => {
  it('renders the chronology page with dynasty bands and clickable 王昶 bar', () => {
    cy.intercept('GET', '**/api/sino/chronology*').as('chronoApi')
    cy.visit('/chronology')
    cy.wait('@chronoApi', { timeout: 20000 })

    // dynasty band labels are rendered in the SVG
    cy.get('.timeline-svg .dynasty-label', { timeout: 20000 }).should('have.length.at.least', 1)

    // 王昶 lifespan bar is present and clickable
    cy.get('.person-bar[data-id="person-wang-chang"]', { timeout: 20000 }).should('exist')
    cy.get('.person-bar[data-id="person-wang-chang"] .hit-area').click()
    cy.url({ timeout: 10000 }).should('include', '/people/person-wang-chang')
  })

  it('shows 金石萃編 work marker linking to the work page', () => {
    cy.intercept('GET', '**/api/sino/chronology*').as('chronoApi')
    cy.visit('/chronology')
    cy.wait('@chronoApi', { timeout: 20000 })

    cy.get('.work-marker[data-id="work-000002"]', { timeout: 20000 }).should('exist')
    cy.get('.work-marker[data-id="work-000002"] polygon:last-child').click({ force: true })
    cy.url({ timeout: 10000 }).should('include', '/works/work-000002')
  })

  it('renders floruit-only persons with hatched fill', () => {
    cy.intercept('GET', '**/api/sino/chronology*').as('chronoApi')
    cy.visit('/chronology')
    cy.wait('@chronoApi', { timeout: 20000 })

    // floruit persons get fill="url(#fh-full)" not a solid colour
    cy.get('.person-bar .person-floruit', { timeout: 20000 })
      .should('have.length.at.least', 1)
      .first()
      .should('have.attr', 'fill')
      .and('match', /url\(#fh-full\)/)
  })

  it('shows a mini-timeline on the person detail page', () => {
    cy.intercept('GET', '**/api/sino/chronology*').as('chronoApi')
    cy.visit('/people/person-wang-chang')
    cy.wait('@chronoApi', { timeout: 20000 })

    cy.get('.mini-timeline[data-entity-type="person"]', { timeout: 5000 }).should('exist')
    cy.get('.mini-timeline .mini-timeline-svg', { timeout: 10000 }).should('exist')
  })

  it('shows the 乙瑛碑 attestation strip with origin and attestation markers', () => {
    cy.visit('/jinshi-inscriptions/insc-000001')
    cy.get('.attestation-strip', { timeout: 20000 }).should('exist')
    // attestation strip SVG renders after page load
    cy.get('.attestation-strip .attestation-strip-svg', { timeout: 15000 }).should('exist')
    // origin marker (filled circle for the stone's creation date)
    cy.get('.attestation-strip-svg circle', { timeout: 10000 })
      .should('have.length.at.least', 2)
    // at least one attestation marker links back via the att-marker click handler
    cy.get('.attestation-strip-svg .att-marker').should('have.length.at.least', 1)
  })

  it('full Qing view renders without timeout', () => {
    cy.intercept('GET', '**/api/sino/chronology?dynasty=qing*').as('qingApi')
    cy.visit('/chronology')
    // click the Qing dynasty filter button
    cy.get('.dynasty-btn', { timeout: 20000 }).contains('清').click()
    cy.wait('@qingApi', { timeout: 30000 })
    cy.get('.timeline-svg', { timeout: 20000 }).should('exist')
  })
})
