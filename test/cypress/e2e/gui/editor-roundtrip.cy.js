// The regression keystone for the editor port (M3): create an inscription
// through the UI, save it, reopen it and verify the content survived.

describe('Inscription editor roundtrip', () => {
  const TITLE = '測試造像記 Test votive stele'
  const createdIds = []

  afterEach(() => {
    // remove documents created by this spec straight from the database
    createdIds.forEach(id => {
      cy.request({
        method: 'DELETE',
        url: `http://localhost:8080/exist/rest/db/apps/edep-sino-data/data/workspace/${id}.xml`,
        auth: { user: 'admin', pass: '' },
        failOnStatusCode: false
      })
    })
  })

  it('creates, saves and reopens an inscription losslessly', () => {
    cy.login()
    cy.visit('/edit.html')

    cy.get('fx-fore#epidoc-editor', { timeout: 20000 }).should('exist')
    cy.get('#edeptitle input', { timeout: 20000 })
      .should('be.visible')
      .type(TITLE, { force: true })

    // save: button sits inside pb-restricted, revealed for the tei group
    cy.get('section.buttonBar .saveBtn button', { timeout: 20000 })
      .should('be.visible')
      .click()

    // after create the page URL carries the assigned EDEp id
    cy.url({ timeout: 20000 }).should('match', /[?&]id=E\d+/)

    cy.url().then(u => {
      const id = new URL(u).searchParams.get('id')
      createdIds.push(id)

      // the document landed in the workspace with idno + title
      cy.request(`/api/inscription?id=${id}&collection=workspace`)
        .its('body')
        .should('include', TITLE)
        .and('include', `<idno type="EDEp">${id}</idno>`)

      // reopen through the UI: the form repopulates from the stored XML
      cy.visit(`/edit.html?id=${id}&collection=workspace`)
      cy.get('#edeptitle input', { timeout: 20000 }).should('have.value', TITLE)

      // save again (no changes): document stays stable, only a revision
      // change entry is appended by design
      cy.get('section.buttonBar .saveBtn button', { timeout: 20000 })
        .should('be.visible')
        .click()
      cy.get('#edeptitle input', { timeout: 10000 }).should('have.value', TITLE)
      cy.request(`/api/inscription?id=${id}&collection=workspace`)
        .its('body')
        .should('include', TITLE)
    })
  })

  it('creates a fragment linked to its parent', () => {
    cy.login()
    cy.visit('/edit.html')
    cy.get('#edeptitle input', { timeout: 20000 })
      .should('be.visible')
      .type('碑陽 parent for fragment', { force: true })
    cy.get('section.buttonBar .saveBtn button', { timeout: 20000 })
      .should('be.visible').click()
    cy.url({ timeout: 20000 }).should('match', /[?&]id=E\d+/)

    cy.url().then(u => {
      const id = new URL(u).searchParams.get('id')
      createdIds.push(id)

      // the fragment block in the nav shows the add button (parent has xml:id)
      cy.get('#addFragment button', { timeout: 20000 }).should('be.visible').click()

      // the parent gains a space-separated @fragments list; read the real
      // assigned fragment id from it (id may not be "-1" if siblings exist)
      cy.get('#r-fragments a', { timeout: 20000 })
        .last()
        .invoke('text')
        .then(fragId => {
          const fid = fragId.trim()
          createdIds.push(fid)
          cy.request(`/api/inscription?id=${fid}&collection=workspace`)
            .its('body')
            .should('include', `corresp="${id}"`)
            .and('include', 'type="partial"')
        })
    })
  })
})
