// M8: sino register entries can be created through the registers API and
// render with their name components / hierarchy (doc/sino-model.md par.6-7).

describe('Sino register entries', () => {
  const created = []

  after(() => {
    created.forEach(id => {
      cy.request({
        method: 'DELETE',
        url: `/api/register/${id}`,
        failOnStatusCode: false
      })
    })
  })

  it('creates a person with 字/諡/官職 and renders the components', () => {
    cy.login()
    const person = `<person xmlns="http://www.tei-c.org/ns/1.0" xml:id="person-NEW" role="official">
        <persName type="canonical" xml:lang="zh">顏真卿</persName>
        <persName xml:lang="zh-Latn-pinyin">Yan Zhenqing</persName>
        <persName type="sort">Yan Zhenqing</persName>
        <addName type="zi" xml:lang="zh">清臣</addName>
        <addName type="posthumous" xml:lang="zh">文忠</addName>
        <floruit notBefore="0709" notAfter="0784"/>
        <persState type="office"><label xml:lang="zh">太子太師</label></persState>
        <note type="bio" xml:lang="en">Tang calligrapher and statesman (test entry).</note>
      </person>`

    cy.request({
      method: 'PUT',
      url: '/api/register',
      body: person,
      headers: { 'content-type': 'application/xml' }
    }).then(({ status, body }) => {
      expect(status).to.eq(200)
      const m = String(body).match(/xml:id="(person-\d+)"/)
      expect(m, 'assigned id').to.not.be.null
      const id = m[1]
      created.push(id)

      cy.request(`/api/register/${id}/html`).its('body').then(html => {
        expect(html).to.include('顏真卿')
      })
      // detail page renders the full sino component set
      cy.request(`/people/${id}`).its('body').then(html => {
        expect(html).to.include('清臣')        // 字
        expect(html).to.include('文忠')        // 諡
        expect(html).to.include('太子太師')    // office
        expect(html).to.include('fl. 0709')   // floruit
      })
    })
  })

  it('creates a place with dated historical names and admin hierarchy', () => {
    cy.login()
    const place = `<place xmlns="http://www.tei-c.org/ns/1.0" xml:id="place-NEW" type="settlement">
        <placeName type="main" xml:lang="zh">洛陽</placeName>
        <placeName xml:lang="zh-Latn-pinyin">Luoyang</placeName>
        <placeName type="sort">Luoyang</placeName>
        <placeName type="historical" xml:lang="zh" notBefore="0025" notAfter="0220">雒陽</placeName>
        <region type="zhou" xml:lang="zh" notBefore="0618" notAfter="0907">都畿道</region>
        <region type="fu" xml:lang="zh" notBefore="0618" notAfter="0907">河南府</region>
        <location><geo>34.6197 112.4540</geo></location>
        <ptr type="tgaz" target="https://maps.cga.harvard.edu/tgaz/placename/hvd_80785"/>
        <note xml:lang="en">Test entry.</note>
      </place>`

    cy.request({
      method: 'PUT',
      url: '/api/register',
      body: place,
      headers: { 'content-type': 'application/xml' }
    }).then(({ status, body }) => {
      expect(status).to.eq(200)
      const m = String(body).match(/xml:id="(place-\d+)"/)
      expect(m, 'assigned id').to.not.be.null
      const id = m[1]
      created.push(id)

      cy.request(`/places/${id}`).its('body').then(html => {
        expect(html).to.include('洛陽')
        expect(html).to.include('古名')                 // historical names row
        expect(html).to.include('雒陽')
        expect(html).to.include('政區')                 // admin hierarchy row
        expect(html).to.include('河南府')
        expect(html).to.include('tgaz')
      })
    })
  })
})
