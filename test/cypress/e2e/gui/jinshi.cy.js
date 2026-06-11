// M-J1: jinshi history layer GUI — register list pages, detail navigation and
// the editor's authority cross-reference field (idno type="jinshi").

describe('Jinshi registers GUI', () => {
  it('browses the works register and opens a work', () => {
    cy.intercept('GET', '**/api/works*').as('worksApi')
    cy.visit('/works')
    cy.wait('@worksApi', { timeout: 20000 })
    cy.get('pb-split-list', { timeout: 20000 }).should('exist')
    cy.get('.split-list-item a[href*="works/work-000002"]', { timeout: 20000 })
      .first()
      .click({ force: true })
    cy.url({ timeout: 10000 }).should('include', '/works/work-000002')
    cy.get('.work.jinshi-detail h1', { timeout: 20000 })
      .should('contain.text', '金石萃編')
    // recorded inscriptions join is rendered with a link into the catalogue
    cy.get('.recorded-inscriptions a[href*="jinshi-inscriptions/insc-000001"]')
      .should('exist')
  })

  it('browses the inscription catalogue and reads the attestation timeline', () => {
    cy.intercept('GET', '**/api/jinshi-inscriptions*').as('jinshiApi')
    cy.visit('/jinshi-inscriptions')
    cy.wait('@jinshiApi', { timeout: 20000 })
    cy.get('.split-list-item a[href*="jinshi-inscriptions/insc-000001"]', { timeout: 20000 })
      .first()
      .click({ force: true })
    cy.url({ timeout: 10000 }).should('include', '/jinshi-inscriptions/insc-000001')
    cy.get('.jinshi-inscription h1', { timeout: 20000 }).should('contain.text', '乙瑛碑')
    cy.get('.attestation-list li').should('have.length.at.least', 2)
    // first attestation in the reception timeline is the oldest work (集古錄)
    cy.get('.attestation-list li').first().find('a[href*="works/work-000001"]').should('exist')
    cy.get('.rubbings a[href*="digitalarchive.npm.gov.tw"]').should('exist')
  })

  it('loads and preserves the authority id in the editor (roundtrip)', () => {
    cy.login()
    cy.visit('/edit.html?id=demo-zaoxiangji&collection=workspace')
    cy.get('fx-fore#epidoc-editor', { timeout: 20000 }).should('exist')

    // the identifier section shows the authority id loaded from the document
    cy.get('#jinshi-id input', { timeout: 20000 })
      .should('have.value', 'insc-demo-000001')

    // save and verify the cross-reference survives the postprocess pipeline
    cy.get('section.buttonBar .saveBtn button', { timeout: 20000 })
      .should('be.visible').click()
    cy.get('#edeptitle input', { timeout: 20000 })
      .should('have.value', '測試造像記（示範樣本 demo sample）')
    cy.request('/api/inscription?id=demo-zaoxiangji&collection=workspace')
      .its('body').then(xml => {
        expect(xml).to.include('<idno type="jinshi">insc-demo-000001</idno>')
      })
  })

  it('shows the authority block on the document view', () => {
    cy.visit('/demo-zaoxiangji.xml')
    cy.get('.jinshi-authority', { timeout: 20000 }).should('exist')
    cy.get('.jinshi-authority a[href*="jinshi-inscriptions/insc-demo-000001"]')
      .should('contain.text', '測試造像記')
  })
})
