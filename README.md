<img src="https://upload.wikimedia.org/wikipedia/commons/thumb/7/7c/Google_Summer_of_Code_sun_logo_2022.svg/1024px-Google_Summer_of_Code_sun_logo_2022.svg.png" height="100"/><img src="https://icons.veryicon.com/png/o/internet--web/social-1/at-symbol.png" height="80"/><img src="https://blog.wellcomeopenresearch.org/wp-content/uploads/2021/05/Untitled-design-2021-05-19T101505.875-300x200.png" height="100"/><img src="https://icons.veryicon.com/png/o/internet--web/social-1/at-symbol.png" height="80"/><img src="https://d2q79iu7y748jz.cloudfront.net/s/_squarelogo/256x256/7167d385ff2b5a5105a9ba3bd271bb1d" height="100"/>

[Google Summer of Code](https://summerofcode.withgoogle.com) at the [Tree of Life](https://www.sanger.ac.uk/programme/tree-of-life/) at the [Wellcome Sanger Institute](https://www.sanger.ac.uk)

[**Accepting proposals for Google Summer of Code 2024**](https://docs.google.com/document/d/1vWnJhxWJU4oNsZNheKrP6sx5ZPkOzumwdnL6IIRbDP4)

# GoaT-NLP

_**Natural language search across the tree of life**_

The [Tree of Life](https://www.sanger.ac.uk/programme/tree-of-life/) at the [Wellcome Sanger Institute](https://www.sanger.ac.uk) is generating high-quality genome assemblies as part of the [Earth BioGenome Project (EBP)](https://www.earthbiogenome.org), a global initiative to generate reference-quality genome sequences for all species on earth. Given the scale of this initiative, we need ready access to metadata relevant to sample collection, sequencing and assembly and a platform to coordinate our efforts with those of other projects under the EBP umbrella. To meet this need, we have developed [Genomes on a Tree (GoaT)](https://goat.genomehubs.org), an [Elasticsearch](https://www.elastic.co/elasticsearch)-based datastore, search engine, and reporting platform, with directly-measured or estimated values for a suite of attributes across all known species.

This project is about bridging the gap between the potential of GoaT to perform queries relevant to all stages of the biodiversity genomics projects within the EBP and users' ability to formulate these queries using the syntax that the existing API, CLI and front end UI require. To be able to directly answer questions like:

- Which plant families do not yet have a reference-quality genome assembly for any species? [[UI result table](https://goat.genomehubs.org/search?result=taxon&includeEstimates=true&taxonomy=ncbi&query=tax_tree%2833090%5BViridiplantae%5D%29%20AND%20tax_rank%28family%29%20AND%20ebp_standard_date%3Dnull)]
- How many butterfly species without an assembly have an expected genome size greater than 1 billion base pairs? [[API `/count` endpoint](https://goat.genomehubs.org/search?result=taxon&includeEstimates=true&taxonomy=ncbi&query=tax_tree%287088%5BLepidoptera%5D%29%20AND%20tax_rank%28species%29%20AND%20assembly_level%3Dnull%20AND%20genome_size%3E1000000000)]
- Which species on a project target list are already being sequenced by another EBP partner project? [[API `/search` endpoint](https://goat.genomehubs.org/search?result=taxon&includeEstimates=true&taxonomy=ncbi&query=tax_tree%282759%5BEukaryota%5D%29%20AND%20tax_rank%28species%29%20AND%20long_list%3DDTOL%20AND%20in_progress%3D%21DTOL&fields=long_list%2Cin_progress)]
- What proportion of reference-quality genome assemblies have been produced by EBP vs non-EBP projects in each of the last 5 years? [[UI report view for 1 year](https://goat.genomehubs.org/search?result=taxon&includeEstimates=true&taxonomy=ncbi&size=50&query=bioproject%3DPRJNA533106%20AND%20tax_rank%28species%29&fields=ebp_standard_date%2Cassembly_level%2Cassembly_span%2Cbioproject&report=arc&rank=species&pointSize=15&cat=bioproject%5B1%2B%5D&y=tax_tree%282759%5BEukaryota%5D%29%20AND%20ebp_standard_date%3E%3D2023%20AND%20ebp_standard_date%3C2024)]

## GenomeHubs project

GoaT is part of a broader collection of tools developed under the GenomeHubs project. A closely related tool, BoaT, indexes data within assemblies, and it is anticipated that development of GoaT-NLP will also benefit BoaT and further GenomeHubs projects still in development. All GenomeHubs source code is open source under the MIT license avaliable from the [GenomeHubs GitHub organisation](https://github.com/genomehubs), primarily in the [genomehubs/genomehubs](https://github.com/genomehubs/genomehubs) repository. Configuration files to define the source data and customise the UI for GoaT are in the [genomehubs/goat-data](https://github.com/genomehubs/goat-data) and the [genomehubs/goat-ui](https://github.com/genomehubs/goat-ui) repositories, respectively.

### Data structure

In order to support queries like the examples above, GoaT stores directly measured and estimated values for a range of attributes alongside taxonomic information including rank and lineage as a document per taxon in the datastore. The data structure for the taxon index is summarised below, other datatypes including assembly, sample and features are stored in separate indexes.

A processed taxon document can be obtained from the `/record` endpoint of the API, e.g. [/api/v2/record?recordId=9612&result=taxon](https://goat.genomehubs.org/api/v2/record?recordId=9612&result=taxon) or viewed in the UI by visiting the correwsponding taxon record page, e.g. [/record?recordId=9612&result=taxon](https://goat.genomehubs.org/record?recordId=9612&result=taxon).

Each document has a core set of keyword fields:

- `taxon_id` - unique taxon ID in the current taxonomy (defaut NCBI taxonomy)
- `parent` - taxon ID of the parent taxon
- `scientific_name` - scientific name of the taxon
- `taxon_rank` - rank of the taxon, e.g. species, genus, family, etc.

Additional fields are divided into three groups:

### `taxon_names:`

A set of nested fields for each name of the taxon:

- `name` - the taxon name
- `class` - the taxon name class, e.g. scientific name, common name, etc.
- `source` - the source of the taxon name, e.g. NCBI, GBIF, etc.

### `lineage:`

An ordered set of nested fields for each ancestor of the taxon:

- `taxon_id` - the unique ID of the ancestral taxon
- `taxon_rank` - the rank of the ancestral taxon
- `scientific_name` - the scientific name of the ancestral taxon
- `node_depth` - the depth of the ancestral taxon in the taxonomic tree

### `attributes:`

A set of nested fields for each attribute:

- `key` - the unique attribute name
- `*_value` - the summary value of the attribute where `*` is the attribute type which largely corresponds to the list of Elasticsearch [field data types](https://www.elastic.co/guide/en/elasticsearch/reference/current/mapping-types.html)
- `source` - the source of the attribute, e.g. NCBI, GBIF, etc.
- `min`, `max`, `mean`, `median` - summary statistics for the attribute
- `aggregation_method` - the aggregation method used to generate a summary value
- `aggregation_source` - the source of the attribute used to generate a summary value (direct, ancestor, descendant)

Each attribute value in the taxon index can be derived from one or more raw values, which are stored as a nested set of values in the `values` field.

The full mapping used is defined in [`taxon.json`](https://github.com/genomehubs/genomehubs/blob/main/src/genomehubs/templates/taxon.json). Similar mappings are used for the other document types.

### Query syntax

The query syntax currently used by GoaT it tied to this structured data model. It supports simple and highly-specific queries, but takes time to learn and presents a barrier to wider data access.

GoaT query syntax allows any combination of of `tax_` filters and `<attribute>` `<operator>` `<value>` clauses to be joined with `AND` operators.

`tax_` filters are used to restrict the taxonomic scope of a query as follows:

- `tax_name(<value>)` - return results where any taxon name or ID at the top-level or in `taxon_names` matches `value`
- `tax_tree(<value>)` - return results where the name or taxon ID of any taxon in the `lineage` matches `value`
- `tax_rank(<value>)` - return results where the `taxon_rank` matches `value`
- `tax_depth(<value>)` - return results where the `node_depth` of any taxon in the `lineage` < `value`
- `tax_lineage(<value>)` - return results for each ancestral taxon in the `lineage` of a record where any taxon name or ID at the top-level or in `taxon_names` matches `value`

The operators supported are: `=`, `!=`, `>`, `>=`, `<`, and `<=`. A full list of available atttribute names, types and value constraints is available at [goat.genomehubs.org/types](https://goat.genomehubs.org/types).

Support for logical `OR` operators is currently limited to the ability to provide a comma separated list of values for an attribute or tax_filter, in which case results will be returned if at least one value matches the query. For example, `tax_tree(fungi,metazoa) AND long_list(DTOL,GAGA)` will return results for taxa in either the fungi or metazoa lineage and where the `long_list` attribute contains either `DTOL` or `GAGA`.

Values of summary statistics can also be queried using the `min`, `max`, `mean`, `median` modifiers, e.g. using `min(assembly_date)>=2023-01-01` to find taxa by the earliest assembly date.

## Natural language search

GoaT-NLP aims to extend the capabilities of GoaT to support natural language queries. The project aims to:

- Take natural language queries and convert them to structured queries using the GoaT query syntax.

  ![Static Badge](https://img.shields.io/badge/priority-highest-54278f)

- Automatically select the most appropriate type of search to perform and return results as a natural language statement.

  ![Static Badge](https://img.shields.io/badge/priority-high-756bb1)

- Augment Goat search results with extracts from unstructured text.

  ![Static Badge](https://img.shields.io/badge/priority-medium-9e9ac8)

- Extract information from text using machine learning models for indexing.

  ![Static Badge](https://img.shields.io/badge/priority-low-cbc9e2)

## Contributing

We are proposing the GoaT-NLP project as a Google Summer of Code project for 2024. If you are interested in contributing to GoaT-NLP, please read the information provided in the [ToL+PaM GSoC 2024 Google Doc](https://docs.google.com/document/d/1vWnJhxWJU4oNsZNheKrP6sx5ZPkOzumwdnL6IIRbDP4) and use the information in that document to get in touch with any questions you may have.

### Proposals

We will assess applications from potential GSoC contributors on the basis of the proposal. Again, see the [ToL+PaM GSoC 2024 Google Doc](https://docs.google.com/document/d/1vWnJhxWJU4oNsZNheKrP6sx5ZPkOzumwdnL6IIRbDP4) for more, but broadly, we want to know:

- how would approach this project?
- which technologies would you use and why?
- what would be the key milestones and when would you reach them?
- how would you ensure the sustainability of your code beyond the end of the GSoC term?

## Resources

- [GoaT paper](https://wellcomeopenresearch.org/articles/8-24)
- [GoaT website](https://goat.genomehubs.org)
- [API documentation](https://goat.genomehubs.org/api/v2/api-docs)
- [GenomeHubs codebase](https://github.com/genomehubs/genomehubs)
- [BoaT website](https://boat.genomehubs.org)
- [Tree of Life](https://www.sanger.ac.uk/programme/tree-of-life/)
- [Earth BioGenome Project](https://www.earthbiogenome.org)
- [Google Summer of Code](https://summerofcode.withgoogle.com)
- [ToL+PaM GSoC 2024 Google Doc](https://docs.google.com/document/d/1vWnJhxWJU4oNsZNheKrP6sx5ZPkOzumwdnL6IIRbDP4)
