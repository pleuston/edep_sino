// M9: reading view of a Chinese inscription — vertical columns by default,
// horizontal fallback toggle, variant-glyph popover, zh_TW interface.

describe('Document view (sino rendering)', () => {
  it('renders the lzh edition vertically with a working toggle', () => {
    cy.visit('/demo-zaoxiangji.xml')

    cy.get('pb-view', { timeout: 30000 }).should('exist')
    cy.get('pb-view').shadow().find('.tei-ab[lang="lzh"], [lang="lzh"] .tei-ab', { timeout: 30000 })
      .first()
      .should($ab => {
        const wm = getComputedStyle($ab[0]).writingMode
        expect(wm, 'vertical by default').to.eq('vertical-rl')
      })

    // the toggle flips to horizontal via the custom property
    cy.get('button.cjk-direction-toggle').click()
    cy.get('pb-view').shadow().find('.tei-ab[lang="lzh"], [lang="lzh"] .tei-ab')
      .first()
      .should($ab => {
        const wm = getComputedStyle($ab[0]).writingMode
        expect(wm, 'horizontal after toggle').to.eq('horizontal-tb')
      })
    cy.get('button.cjk-direction-toggle').click()

    cy.screenshot('document-vertical', { capture: 'viewport', overwrite: true })
  })

  it('shows the variant glyph with its standardized mapping', () => {
    cy.visit('/demo-zaoxiangji.xml')
    cy.get('pb-view', { timeout: 30000 }).shadow()
      .find('.tei-g', { timeout: 30000 }).should('exist')
    cy.get('pb-view').shadow().find('.tei-g pb-popover, pb-popover .tei-g, .tei-g')
      .first().should('exist')
  })

  it('presents the interface in Traditional Chinese', () => {
    cy.visit('/edit.html?lang=zh_TW')
    cy.get('fx-fore#epidoc-editor', { timeout: 20000 }).should('exist')
    // the save button label resolves through app/zh_TW.json
    cy.get('section.buttonBar', { timeout: 20000 })
      .should('contain.text', '儲存')
    // a section heading from the sino additions
    cy.get('details#witnesses summary').should('contain.text', '文本載體')
  })
})
