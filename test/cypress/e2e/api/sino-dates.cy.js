// API tests for the Chinese era-date conversion service (doc/sino-model.md par.1)

describe('Sino dating API', () => {
  it('converts 永和九年 to 0353 with exact lunisolar bounds and ganzhi check', () => {
    cy.request(`/api/sino/era?name=${encodeURIComponent('永和')}&year=9&ganzhi=${encodeURIComponent('癸丑')}`)
      .then(({ status, body }) => {
        expect(status).to.eq(200)
        const doc = new DOMParser().parseFromString(body, 'application/xml')
        const eras = [...doc.querySelectorAll('era')]
        expect(eras.length, 'multiple dynasties share the era name').to.be.greaterThan(3)
        const dongjin = eras.find(e => e.getAttribute('dynasty') === '東晉')
        expect(dongjin, 'Eastern Jin candidate').to.not.be.undefined
        expect(dongjin.getAttribute('when')).to.eq('0353')
        expect(dongjin.getAttribute('notBefore')).to.eq('0353-02-21')
        expect(dongjin.getAttribute('notAfter')).to.eq('0354-02-09')
        expect(dongjin.getAttribute('nToken')).to.eq('永和九年')
        expect(dongjin.getAttribute('gz')).to.eq('癸丑')
        expect(dongjin.getAttribute('gzMatch')).to.eq('true')
        expect(dongjin.getAttribute('period')).to.eq('sino:dynasty:dongjin')
      })
  })

  it('flags a ganzhi mismatch', () => {
    cy.request(`/api/sino/era?name=${encodeURIComponent('永和')}&year=9&ganzhi=${encodeURIComponent('甲子')}&dynasty=${encodeURIComponent('東晉')}`)
      .then(({ body }) => {
        const doc = new DOMParser().parseFromString(body, 'application/xml')
        const era = doc.querySelector('era[dynasty="東晉"]')
        expect(era.getAttribute('gzMatch')).to.eq('false')
        expect(era.getAttribute('gz'), 'reports the expected cyclical year').to.eq('癸丑')
      })
  })

  it('marks reign years outside the era span', () => {
    cy.request(`/api/sino/era?name=${encodeURIComponent('永和')}&year=9&dynasty=${encodeURIComponent('東漢')}`)
      .then(({ body }) => {
        const doc = new DOMParser().parseFromString(body, 'application/xml')
        // Eastern Han 永和 ran 136-142: year 9 does not exist
        expect(doc.querySelector('era').getAttribute('yearOutOfRange')).to.eq('true')
      })
  })

  it('returns an era range when no reign year is given', () => {
    cy.request(`/api/sino/era?name=${encodeURIComponent('開元')}`)
      .then(({ body }) => {
        const doc = new DOMParser().parseFromString(body, 'application/xml')
        const tang = [...doc.querySelectorAll('era')].find(e => e.getAttribute('dynasty') === '唐')
        expect(tang.getAttribute('notBefore')).to.eq('0713')
        expect(tang.getAttribute('notAfter')).to.eq('0742')
      })
  })

  it('serves the era list for autocomplete', () => {
    cy.request('/api/sino/eras').then(({ body }) => {
      const doc = new DOMParser().parseFromString(body, 'application/xml')
      expect(doc.querySelectorAll('e').length).to.be.greaterThan(900)
    })
  })
})
