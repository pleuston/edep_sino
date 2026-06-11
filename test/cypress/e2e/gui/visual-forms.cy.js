// M12: visual forms (objectDesc/@form + sealDesc) and the inline inscription
// list on site pages.

describe('Visual forms and site holdings', () => {
  it('lists the inscriptions on the site (place) page', () => {
    cy.visit('/places/place-yunfengshan')
    cy.get('.site-holdings', { timeout: 20000 }).should('exist')
    cy.get('.site-holdings .site-inscriptions a')
      .should('have.length.greaterThan', 0)
      .first()
      .should('have.attr', 'href')
      .and('include', 'demo-zaoxiangji.xml')
    cy.get('.site-holdings h2').should('contain.text', '(1)')
  })

  it('loads the visual form and seal from the demo into the editor', () => {
    cy.login()
    cy.visit('/edit.html?id=demo-zaoxiangji&collection=workspace')
    cy.get('fx-fore#epidoc-editor', { timeout: 20000 }).should('exist')

    cy.get('details#objectdesc').invoke('attr', 'open', 'open')
    // visual form select repopulated from objectDesc/@form
    cy.get('#visual-form select', { timeout: 20000 })
      .find('option:selected')
      .should('have.value', 'sino:medium:keshi')
    // seal row present with its type and legend
    cy.get('#r-seals select').first().should('have.value', 'sino:sealtype:jiancang')
    cy.get('#r-seals input').filter((i, el) => el.value === '示範藏印（樣本）')
      .should('have.length', 1)
  })

  it('preserves visual form and seals across a UI save', () => {
    cy.login()
    cy.visit('/edit.html?id=demo-zaoxiangji&collection=workspace')
    cy.get('#edeptitle input', { timeout: 20000 })
      .should('have.value', '測試造像記（示範樣本 demo sample）')
    cy.get('section.buttonBar .saveBtn button', { timeout: 20000 })
      .should('be.visible').click()
    cy.get('#edeptitle input', { timeout: 20000 })
      .should('have.value', '測試造像記（示範樣本 demo sample）')

    cy.request('/api/inscription?id=demo-zaoxiangji&collection=workspace')
      .its('body').then(xml => {
        expect(xml).to.include('form="sino:medium:keshi"')
        expect(xml).to.include('<sealDesc>')
        expect(xml).to.include('sino:sealtype:jiancang')
        expect(xml).to.include('示範藏印')
        // empty placeholder attrs were stripped, document still EpiDoc-valid shape
        expect(xml).to.not.include('corresp=""')
      })
  })
})
