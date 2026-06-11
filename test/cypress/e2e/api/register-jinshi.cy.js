// M-J1: jinshi history layer — works register 金石著作 + inscription authority
// register 石刻總目 (doc/sino-model.md par.10). Proves the register machinery
// fixes: id assignment for bibl/object records and bibliography scoping.

describe('Jinshi registers API', () => {
  it('assigns an id to a new work record (bibl, work-NEW)', () => {
    cy.login()
    const work = `<bibl xmlns="http://www.tei-c.org/ns/1.0" xml:id="work-NEW" type="work">
        <title xml:lang="zh">測試金石著作</title>
        <title xml:lang="zh-Latn-x-pinyin">Ceshi jinshi zhuzuo</title>
        <author><persName corresp="person-wang-chang" xml:lang="zh">王昶</persName></author>
        <date type="compiled" when="1800">1800（測試）</date>
      </bibl>`

    cy.request({
      method: 'PUT',
      url: '/api/register',
      body: work,
      headers: { 'content-type': 'application/xml' }
    }).then(({ status, body }) => {
      expect(status).to.eq(200)
      // without the prepare-record fix the record keeps xml:id="work-NEW"
      const m = String(body).match(/xml:id="(work-\d+)"/)
      expect(m, 'assigned work id').to.not.be.null
      const id = m[1]

      // the record is retrievable and the detail page renders
      cy.request(`/works/${id}`).its('body').then(html => {
        expect(html).to.include('測試金石著作')
        expect(html).to.include('Ceshi jinshi zhuzuo')
      })
    })
  })

  it('assigns an id to a new inscription authority record (object, insc-NEW)', () => {
    cy.login()
    const object = `<object xmlns="http://www.tei-c.org/ns/1.0" xml:id="insc-NEW">
        <objectIdentifier>
          <objectName type="main" xml:lang="zh">測試刻石（API）</objectName>
          <objectName type="sort" xml:lang="zh-Latn-x-pinyin">Ceshi keshi API</objectName>
        </objectIdentifier>
      </object>`

    cy.request({
      method: 'PUT',
      url: '/api/register',
      body: object,
      headers: { 'content-type': 'application/xml' }
    }).then(({ status, body }) => {
      expect(status).to.eq(200)
      const m = String(body).match(/xml:id="(insc-\d+)"/)
      expect(m, 'assigned inscription id').to.not.be.null
      const id = m[1]

      cy.request(`/jinshi-inscriptions/${id}`).its('body').then(html => {
        expect(html).to.include('測試刻石（API）')
      })
    })
  })

  it('keeps the bibliography register scoped (works do not leak in)', () => {
    // runs after the work creation above: pb-works now holds extra bibl
    // elements (works + nested editions); the bibliography list must still
    // contain only entries of the pb-bibl register document
    cy.request('/api/bibliography/all').its('body').then(list => {
      const ids = list.map(e => e.id)
      expect(ids).to.include('bibl-yzjsh')
      ids.forEach(id => {
        expect(id, 'bibliography entry id').to.not.match(/^work-/)
        expect(id, 'bibliography entry id').to.not.match(/^insc-/)
      })
    })
  })

  it('lists the seed works and inscriptions', () => {
    cy.request('/api/works/all').its('body').then(list => {
      expect(list.length).to.be.at.least(3)
      const ids = list.map(e => e.id)
      expect(ids).to.include('work-000001') // 集古錄
      expect(ids).to.include('work-000002') // 金石萃編
      const cuibian = list.find(e => e.id === 'work-000002')
      expect(cuibian.name).to.eq('金石萃編')
      expect(cuibian['sort-name']).to.eq('Jinshi cuibian')
    })
    cy.request('/api/jinshi-inscriptions/all').its('body').then(list => {
      const ids = list.map(e => e.id)
      expect(ids).to.include('insc-000001') // 乙瑛碑
      expect(ids).to.include('insc-demo-000001')
    })
  })

  it('derives the inscriptions-recorded list on the work page (attestation join)', () => {
    cy.request('/works/work-000002').its('body').then(html => {
      // editions, relations in both voices, and the derived 著錄石刻 join
      expect(html).to.include('經訓堂刊本')
      expect(html).to.include('石刻史料新編')
      expect(html).to.include('jinshi.rel.models-on')      // outbound: 仿《集古錄》
      expect(html).to.include('jinshi.rel.supplements-by') // inbound, derived: 《八瓊室金石補正》
      expect(html).to.include('乙瑛碑')
      expect(html).to.include('jinshi-inscriptions/insc-000001')
    })
  })

  it('orders the attestation history by work compilation date', () => {
    cy.request('/jinshi-inscriptions/insc-000001').its('body').then(html => {
      expect(html).to.include('永興元年')
      expect(html).to.include('後漢魯相置孔子廟卒史碑') // title-in-work from 集古錄
      expect(html).to.include('digitalarchive.npm.gov.tw') // rubbing surrogate
      const jigulu = html.indexOf('works/work-000001')   // 集古錄, 1063
      const cuibian = html.indexOf('works/work-000002')  // 金石萃編, 1805
      expect(jigulu, '集古錄 present').to.be.greaterThan(-1)
      expect(cuibian, '金石萃編 present').to.be.greaterThan(-1)
      expect(jigulu, 'reception order').to.be.lessThan(cuibian)
    })
  })

  it('lists authored works on the person page', () => {
    cy.request('/people/person-wang-chang').its('body').then(html => {
      expect(html).to.include('person-works')
      expect(html).to.include('金石萃編')
      expect(html).to.include('works/work-000002')
    })
  })

  it('cross-references corpus document and authority record', () => {
    // document view -> authority record (via idno type="jinshi")
    cy.request('/demo-zaoxiangji.xml').its('body').then(html => {
      expect(html).to.include('jinshi-authority')
      expect(html).to.include('jinshi-inscriptions/insc-demo-000001')
    })
    // authority record -> corpus edition (via idno type="corpus")
    cy.request('/jinshi-inscriptions/insc-demo-000001').its('body').then(html => {
      expect(html).to.include('corpus-edition')
      expect(html).to.include('demo-zaoxiangji.xml')
    })
  })
})
