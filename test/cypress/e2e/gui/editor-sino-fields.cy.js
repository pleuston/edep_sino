// M7 acceptance: the demo 造像記 exercises every sino field. Opening it in
// the editor populates the form; saving it back preserves every sino node
// (the lossless gate for the Chinese layer).

describe('Sino fields: demo inscription', () => {
  it('populates the form from the demo document', () => {
    cy.login()
    cy.visit('/edit.html?id=demo-zaoxiangji&collection=workspace')

    cy.get('#edeptitle input', { timeout: 20000 })
      .should('have.value', '測試造像記（示範樣本 demo sample）')

    // layout: columns / chars per column / direction
    cy.get('details#inscription-field').invoke('attr', 'open', 'open')
    cy.get('details#inscription-field input[type="number"]').first()
      .should('have.value', '10')
    cy.get('details#inscription-field select').first()
      .should('have.value', 'writing-mode: vertical-rl')

    // dating populated from when-custom
    cy.get('details#dating').invoke('attr', 'open', 'open')
    cy.get('details#dating .sino-era-row input[list="era-names"]')
      .should('have.value', '太和')
    cy.get('details#dating .sino-era-row input[type="number"]')
      .should('have.value', '22')
    cy.get('#when-iso input').should('have.value', '0498')

    // production roles
    cy.get('details#production').invoke('attr', 'open', 'open')
    cy.get('#r-production input').filter((i, el) => el.value === '張某（樣本）')
      .should('have.length', 1)
    cy.get('#r-production select').first().should('have.value', 'sino:role:zhuan')

    // witness (rubbing)
    cy.get('details#witnesses').invoke('attr', 'open', 'open')
    cy.get('#r-witnesses select').first().should('have.value', 'rubbing')
    cy.get('#r-witnesses input').filter((i, el) => el.value === '拓 0001')
      .should('have.length', 1)
  })

  it('saving the demo preserves every sino node', () => {
    cy.login()
    cy.visit('/edit.html?id=demo-zaoxiangji&collection=workspace')
    cy.get('#edeptitle input', { timeout: 20000 })
      .should('have.value', '測試造像記（示範樣本 demo sample）')

    cy.get('section.buttonBar .saveBtn button', { timeout: 20000 })
      .should('be.visible')
      .click()
    // wait for the save round-trip to replace the instance
    cy.get('#edeptitle input', { timeout: 20000 })
      .should('have.value', '測試造像記（示範樣本 demo sample）')

    cy.request('/api/inscription?id=demo-zaoxiangji&collection=workspace')
      .its('body').then(xml => {
        // dating quartet
        expect(xml).to.include('太和廿二年九月十四日')
        expect(xml).to.include('when="0498"')
        expect(xml).to.include('notBefore="0498-02-08"')
        expect(xml).to.include('when-custom="太和:22"')
        expect(xml).to.include('n="太和二十二年"')
        expect(xml).to.include('period="sino:dynasty:beiwei"')
        // layout & script
        expect(xml).to.include('columns="10"')
        expect(xml).to.include('writtenLines="20"')
        expect(xml).to.include('writing-mode: vertical-rl')
        expect(xml).to.include('sino:script:weibei')
        // production roles
        expect(xml).to.include('key="sino:role:zhuan"')
        expect(xml).to.include('書丹')
        // witness
        expect(xml).to.include('<witness type="rubbing"')
        expect(xml).to.include('拓 0001')
        // glyph bank + transcription phenomena
        expect(xml).to.include('<charDecl>')
        expect(xml).to.include('g-demo-wei')
        expect(xml).to.include('ana="#jiajie"')
        expect(xml).to.include('<sic>戊</sic>')
        expect(xml).to.include('subtype="que-zi"')
        expect(xml).to.include('rend="taitou-ping"')
        expect(xml).to.include('reason="illegible"')
        // language + space discipline
        expect(xml).to.include('xml:lang="lzh"')
        expect(xml).to.include('xml:space="preserve"')
      })
  })
})
