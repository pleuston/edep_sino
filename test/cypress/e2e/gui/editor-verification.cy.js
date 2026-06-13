// M-E1 (核验): the verification state machine. Every edition is draft-by-default
// (doc/sino-model.md §11); promotion to reviewed/verified rides revisionDesc/@status
// and must round-trip through the editor + survive the append-only save pipeline,
// which also preserves the full <change> audit trail (the self-pollution guard).

describe('Editor verification state machine (revisionDesc/@status)', () => {
  it('loads draft status, promotes to verified, and preserves the audit trail', () => {
    cy.login()
    cy.visit('/edit.html?id=HDS_11&collection=workspace')
    cy.get('fx-fore#epidoc-editor', { timeout: 20000 }).should('exist')

    // imported edition is draft-by-default (value readable while collapsed)
    cy.get('#verification-status select', { timeout: 20000 })
      .should('have.value', 'draft')

    // expand the verification accordion so the select is actionable, then promote
    cy.get('details#verification > summary', { timeout: 20000 }).click()
    cy.get('#verification-status select').select('verified', { force: true })
    cy.get('section.buttonBar .saveBtn button', { timeout: 20000 })
      .should('be.visible').click()
    cy.get('#edeptitle input', { timeout: 20000 }).should('exist')

    // the stored XML carries the new status AND still has the original import
    // 'created' change (append-only trail survived the save pipeline)
    cy.request('/api/inscription?id=HDS_11&collection=workspace')
      .its('body').then(xml => {
        expect(xml).to.match(/<revisionDesc[^>]*status="verified"/)
        expect(xml).to.include('who="import-sutras-data"')    // original change preserved
        expect(xml).to.include('source="stonesutras:HDS_11"') // provenance anchor preserved
      })

    // reopen: the select repopulates from the stored status
    cy.visit('/edit.html?id=HDS_11&collection=workspace')
    cy.get('#verification-status select', { timeout: 20000 })
      .should('have.value', 'verified')

    // reset to draft so the spec is idempotent
    cy.get('details#verification > summary', { timeout: 20000 }).click()
    cy.get('#verification-status select').select('draft', { force: true })
    cy.get('section.buttonBar .saveBtn button', { timeout: 20000 })
      .should('be.visible').click()
    cy.get('#edeptitle input', { timeout: 20000 }).should('exist')
    cy.request('/api/inscription?id=HDS_11&collection=workspace')
      .its('body').then(xml => {
        expect(xml).to.match(/<revisionDesc[^>]*status="draft"/)
      })
  })

  it('shows the verification badge on the sutra detail page', () => {
    cy.visit('/sutras/sutra-000001')
    cy.get('.verify-badge', { timeout: 20000 }).should('exist')
  })
})
