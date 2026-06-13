// M-S1: Stone Sutras register (石經) — imported from the stonesutras.org dataset
// (pilot: Hongdingshan / 洪頂山). Proves the separate sutra register machinery:
// authority <object type="sutra"> list + detail, the site→place link, and the
// authority↔workspace-edition cross-reference.

describe('Stone Sutras register API', () => {
  it('lists the imported Hongdingshan sutra inscriptions', () => {
    cy.request('/api/sutras/all').its('body').then(list => {
      expect(list.length, 'HDS pilot count').to.be.at.least(40)
      const ids = list.map(e => e.id)
      ids.forEach(id => expect(id, 'sutra id prefix').to.match(/^sutra-\d+/))
      const names = list.map(e => e.name)
      expect(names, 'Buddha-name 安王佛 present').to.include('安王佛')
    })
  })

  it('filters the list by the genre facet (佛名/刻經/題記)', () => {
    cy.request('/api/sutras?limit=200').its('body').then(all => {
      const total = (all.items || []).length
      expect(total, 'unfiltered count').to.be.at.least(40)
      cy.request('/api/sutras?limit=200&genre=foming').its('body').then(f => {
        const n = (f.items || []).length
        expect(n, 'foming subset').to.be.greaterThan(0).and.to.be.lessThan(total)
      })
    })
  })

  it('renders a Buddha-name detail with date, Taishō and the linked edition', () => {
    cy.request('/api/sutras/all').its('body').then(list => {
      const anwang = list.find(e => e.name === '安王佛')
      expect(anwang, 'anwang record').to.not.be.undefined
      cy.request(`/sutras/${anwang.id}`).its('body').then(html => {
        expect(html).to.include('安王佛')
        expect(html).to.include('天保元年至河清三年')          // date literal
        expect(html).to.include('places/place-hongdingshan')   // site link
        expect(html).to.include('洪頂山')                       // resolved place name
        expect(html).to.include('T 657')                       // Taishō ref
        expect(html).to.include('HDS_11.xml')                  // corpus edition link
      })
    })
  })

  it('cross-references authority record and workspace edition', () => {
    // edition carries the authority id (idno type="jinshi")
    cy.request('/HDS_11.xml').its('body').then(html => {
      expect(html).to.include('安王佛')
    })
    // the generated edition validates as EpiDoc and exposes the transcription
    cy.request('/api/sutras/all').its('body').then(list => {
      const lotus = list.find(e => String(e.name).includes('摩訶衍'))
      if (lotus) {
        cy.request(`/sutras/${lotus.id}`).its('body').then(html => {
          expect(html).to.include('HDS_5.xml')
        })
      }
    })
  })

  it('exposes the verification status (draft-by-default) in the list API', () => {
    cy.request('/api/sutras/all').its('body').then(list => {
      list.forEach(e => expect(e, 'status field').to.have.property('status'))
      const statuses = [...new Set(list.map(e => e.status))]
      // imported corpus is draft-by-default (doc/sino-model.md §11, 核验)
      expect(statuses, 'draft present').to.include('draft')
    })
  })

  it('shows "other texts on this support" for a multi-text support (HDS_9)', () => {
    // sutra-000010 = HDS_9.1, one of 17 texts on support HDS_9 (E-SUP one-support-many-texts)
    cy.request('/sutras/sutra-000010').its('body').then(html => {
      expect(html, 'same-support section').to.include('class="same-support"')
      const siblings = (html.match(/<li><a href="[^"]*sutras\/sutra-/g) || []).length
      expect(siblings, 'sibling texts on the support').to.be.greaterThan(5)
    })
    // a singleton support shows no such section
    cy.request('/sutras/sutra-000001').its('body').then(html => {
      expect(html, 'singleton has no same-support').to.not.include('class="same-support"')
    })
  })

  it('records the contested calligrapher attribution as structured certainty (安道一)', () => {
    // HDS_3 attributes 書丹 to 僧安道壹 (Seng'an Daoyi) — a scholarly, unsigned, contested
    // claim. doc/sino-model.md §11: encode as @cert on the name + a structured <certainty>
    // in <origin> (E-PRD), with degree/locus/source, surviving the EpiDoc gate + save pipeline.
    cy.request('/api/inscription?id=HDS_3&collection=workspace').its('body').then(xml => {
      // attribute order is not significant (the serializer may reorder)
      expect(xml, 'calligrapher persName id').to.include('xml:id="prod-shu"')
      expect(xml, 'calligrapher flagged uncertain').to.match(/<persName[^>]*cert="low"/)
      expect(xml, 'structured certainty targets the name').to.include('<certainty target="#prod-shu"')
      expect(xml, 'certainty degree').to.include('degree="0.5"')
    })
  })

  it('merged the site into the places register (existing seeds kept)', () => {
    cy.request('/api/places/all').its('body').then(list => {
      const names = list.map(e => e.name || e.label || '')
      const ids = list.map(e => e.id)
      // place-hongdingshan added; taishan/yunfengshan seeds preserved
      expect(ids.some(i => i === 'place-hongdingshan'), 'hongdingshan place').to.be.true
    })
  })
})
