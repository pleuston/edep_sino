// EF1: genre (銘文類別) lives in msContents/@class — the canonical home used by the
// corpus editions, the new-doc template and import-sutras-data.py. The editor must
// load it into the genre select and preserve it on save (previously the form bound
// the wrong location, textClass/keywords/term, so an imported genre was invisible).

describe('Editor genre round-trip (msContents/@class)', () => {
  it('loads and preserves an imported sutra edition genre', () => {
    cy.login()
    cy.visit('/edit.html?id=HDS_11&collection=workspace')
    cy.get('fx-fore#epidoc-editor', { timeout: 20000 }).should('exist')

    // the genre select is populated from msContents/@class (HDS_11 = 佛名 foming)
    cy.get('#msc-genre select', { timeout: 20000 })
      .should('have.value', 'sino:typeins:foming')

    // save and verify the genre survives the postprocess/clean pipeline
    cy.get('section.buttonBar .saveBtn button', { timeout: 20000 })
      .should('be.visible').click()
    cy.get('#edeptitle input', { timeout: 20000 }).should('exist')
    cy.request('/api/inscription?id=HDS_11&collection=workspace')
      .its('body').then(xml => {
        expect(xml).to.include('class="sino:typeins:foming"')
      })
  })
})
