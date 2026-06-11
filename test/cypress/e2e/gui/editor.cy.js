// GUI test for the inscription editor (Fore form) — added with the
// EDEp-Sino editor port (M2). Verifies the page renders, Fore initializes,
// taxonomy instances load from the data app and no console errors occur.

describe('Inscription editor', () => {
  it('renders the Fore form with taxonomies and without console errors', () => {
    const consoleErrors = []

    cy.visit('/edit.html', {
      onBeforeLoad (win) {
        const orig = win.console.error
        win.console.error = (...args) => {
          consoleErrors.push(args.map(String).join(' '))
          orig.apply(win.console, args)
        }
      }
    })

    // the Fore root and the form chrome are present
    cy.get('fx-fore#epidoc-editor', { timeout: 20000 }).should('exist')
    cy.get('main.editor nav ul li').should('have.length.greaterThan', 8)

    // Fore finished at least one refresh: the title control rendered a widget
    cy.get('#edeptitle input, #edeptitle .widget', { timeout: 20000 })
      .should('exist')

    // all form sections from the included parts are in the DOM
    ;['findspot', 'objectdesc', 'inscription-field', 'text-description',
      'edition', 'commentary', 'dating', 'historic-relevance', 'editor']
      .forEach(id => cy.get(`details#${id}`).should('exist'))

    // taxonomy fx-instance loaded from ../edep-sino-data and materialized
    // into select options (stub vocabulary ships 4 object types)
    cy.get('#r-objtyp select option', { timeout: 20000 })
      .should('have.length.greaterThan', 1)

    // open the object description section and keep a visual record
    cy.get('details#objectdesc').invoke('attr', 'open', 'open')
    cy.screenshot('editor-render', { capture: 'viewport', overwrite: true })

    // no console errors during load
    cy.then(() => {
      const relevant = consoleErrors.filter(
        e => !/favicon|ResizeObserver loop/i.test(e)
      )
      expect(relevant, `console errors:\n${relevant.join('\n')}`).to.be.empty
    })
  })
})
