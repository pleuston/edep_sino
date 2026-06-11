// UI flow for Chinese dating (doc/sino-model.md par.1): enter era + reign
// year, convert, apply a candidate, save — then reopen and verify both the
// ISO values and the era fields (parsed back from @when-custom) survive.

describe('Inscription editor: Chinese dating', () => {
  const createdIds = []

  afterEach(() => {
    createdIds.forEach(id => {
      cy.request({
        method: 'DELETE',
        url: `http://localhost:8080/exist/rest/db/apps/epiwen-data/data/workspace/${id}.xml`,
        auth: { user: 'admin', pass: '' },
        failOnStatusCode: false
      })
    })
  })

  it('converts 永和九年, applies the Eastern Jin candidate and roundtrips', () => {
    cy.login()
    cy.visit('/edit.html')

    cy.get('#edeptitle input', { timeout: 20000 })
      .should('be.visible')
      .type('蘭亭測試 dating roundtrip', { force: true })

    // open the dating section and fill the era fields
    cy.get('details#dating').invoke('attr', 'open', 'open')
    cy.get('details#dating .sino-era-row input[list="era-names"]')
      .type('永和', { force: true })
    cy.get('details#dating .sino-era-row input[type="number"]')
      .type('9', { force: true })
    cy.get('#sino-convert button').click()

    // candidates appear; apply the Eastern Jin one (gz match shown)
    cy.contains('.sino-candidate', '東晉', { timeout: 20000 })
      .find('button.apply')
      .click()

    // ISO fields were written into the document
    cy.get('#when-iso input').should('have.value', '0353')

    // save and capture the id
    cy.get('section.buttonBar .saveBtn button', { timeout: 20000 })
      .should('be.visible')
      .click()
    cy.url({ timeout: 20000 }).should('match', /[?&]id=E\d+/)

    cy.url().then(u => {
      const id = new URL(u).searchParams.get('id')
      createdIds.push(id)

      // stored document carries ISO + native value + period + nToken
      cy.request(`/api/inscription?id=${id}&collection=workspace`).its('body').then(xml => {
        expect(xml).to.include('when="0353"')
        expect(xml).to.include('notBefore="0353-02-21"')
        expect(xml).to.include('notAfter="0354-02-09"')
        expect(xml).to.include('when-custom="永和:9"')
        expect(xml).to.include('n="永和九年"')
        expect(xml).to.include('period="sino:dynasty:dongjin"')
      })

      // reopen: era fields repopulate from @when-custom
      cy.visit(`/edit.html?id=${id}&collection=workspace`)
      cy.get('details#dating').invoke('attr', 'open', 'open')
      cy.get('details#dating .sino-era-row input[list="era-names"]', { timeout: 20000 })
        .should('have.value', '永和')
      cy.get('details#dating .sino-era-row input[type="number"]')
        .should('have.value', '9')
    })
  })
})
