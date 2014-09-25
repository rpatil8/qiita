#!/usr/bin/env python

from __future__ import division

# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The Qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from unittest import TestCase, main
from xml.etree import ElementTree as ET
from xml.dom import minidom
import StringIO
from tempfile import mkstemp
from os import close, remove, path


from qiita_ware.ebi import (InvalidMetadataError, SampleAlreadyExistsError,
                            NoXMLError, EBISubmission)


class TestEBISubmission(TestCase):
    def setUp(self):
        self.path = path.dirname(path.abspath(__file__)) + '/test_data'

    def test_init(self):
        e = EBISubmission('2', 'Study Title', 'Study Abstract', 'metagenome')

        self.assertEqual(e.study_id, '2')
        self.assertEqual(e.study_title, 'Study Title')
        self.assertEqual(e.study_abstract, 'Study Abstract')
        self.assertEqual(e.investigation_type, 'metagenome')

        self.assertEqual(e.empty_value, 'no_data')

        self.assertEqual(e.study_xml_fp, None)
        self.assertEqual(e.sample_xml_fp, None)
        self.assertEqual(e.experiment_xml_fp, None)
        self.assertEqual(e.run_xml_fp, None)

        self.assertEqual(e.library_strategy, 'POOLCLONE')
        self.assertEqual(e.library_source, 'METAGENOMIC')
        self.assertEqual(e.library_selection, 'unspecified')

        self.assertEqual(e.additional_metadata, {})

    def test_stringify_kwargs(self):
        e = EBISubmission('2', 'Study Title', 'Study Abstract', 'metagenome',
                          impossible_field=1, maybe_possible_field='BOOM')

        self.assertEqual(e.study_id, '2')
        self.assertEqual(e.study_title, 'Study Title')
        self.assertEqual(e.study_abstract, 'Study Abstract')
        self.assertEqual(e.investigation_type, 'metagenome')

        self.assertEqual(e.empty_value, 'no_data')

        self.assertEqual(e.study_xml_fp, None)
        self.assertEqual(e.sample_xml_fp, None)
        self.assertEqual(e.experiment_xml_fp, None)
        self.assertEqual(e.run_xml_fp, None)

        self.assertEqual(e.library_strategy, 'POOLCLONE')
        self.assertEqual(e.library_source, 'METAGENOMIC')
        self.assertEqual(e.library_selection, 'unspecified')

        self.assertEqual(e.additional_metadata,{"impossible_field":"1",
            "maybe_possible_field":"BOOM"})

    def test_get_study_alias(self):
        e = EBISubmission('2', 'Study Title', 'Study Abstract', 'metagenome')
        self.assertEqual(e._get_study_alias(), 'qiime_study_2')

    def test_get_sample_alias(self):
        e = EBISubmission('2', 'Study Title', 'Study Abstract', 'metagenome')
        e.add_sample('foo')
        self.assertEqual(e._get_sample_alias('foo'), 'qiime_study_2:foo')

    def test_get_experiment_alias(self):
        e = EBISubmission('2', 'Study Title', 'Study Abstract', 'metagenome')
        e.add_sample('foo')
        self.assertEqual(e._get_experiment_alias('foo', 0),
                         'qiime_study_2:foo:0')

    def test_get_submission_alias(self):
        e = EBISubmission('2', 'Study Title', 'Study Abstract', 'metagenome')
        obs = e._get_submission_alias()
        exp = 'qiime_submission_2'
        self.assertEqual(obs, exp)

    def test_get_library_name(self):
        e = EBISubmission('2', 'Study Title', 'Study Abstract', 'metagenome')
        obs = e._get_library_name("nasty<business>", 42)
        exp = "nasty&lt;business&gt;:42"
        self.assertEqual(obs, exp)

    def test_add_dict_as_tags_and_values(self):
        e = EBISubmission('2', 'Study Title', 'Study Abstract', 'metagenome')
        elm = ET.Element('TESTING', {'foo': 'bar'})

        e._add_dict_as_tags_and_values(elm, 'foo', {'x': 'y', '>x': '<y'})
        obs = ET.tostring(elm)
        exp = ''.join([v.strip() for v in ADDDICTTEST.splitlines()])
        self.assertEqual(obs, exp)

    def test_generate_study_xml(self):
        submission = EBISubmission('001', 'teststudy', 'test asbstract',
                                   'metagenome')
        xmlelement = submission.generate_study_xml()
        xml = minidom.parseString(ET.tostring(xmlelement))
        xmlstring = xml.toprettyxml(indent='  ', encoding='UTF-8')
        obs_stripped = ''.join([l.strip() for l in xmlstring.splitlines()])
        exp_stripped = ''.join([l.strip() for l in STUDYXML.splitlines()])
        self.assertEqual(obs_stripped, exp_stripped)

    def test_add_sample(self):
        submission = EBISubmission('001', 'teststudy', 'test asbstract',
                                   'metagenome')
        submission.add_sample('test1')
        submission.add_sample('test2')
        samples = submission.samples
        self.assertTrue('test1' in samples and 'test2' in samples)
        with self.assertRaises(SampleAlreadyExistsError):
            submission.add_sample('test1')

    def test_generate_sample_xml(self):
        submission = EBISubmission('001', 'teststudy', 'test asbstract',
                                   'metagenome')
        submission.add_sample('test1')
        submission.add_sample('test2')
        xmlelement = submission.generate_sample_xml()
        xml = minidom.parseString(ET.tostring(xmlelement))
        xmlstring = xml.toprettyxml(indent='  ', encoding='UTF-8')
        obs_stripped = ''.join([l.strip() for l in xmlstring.splitlines()])
        exp_stripped = ''.join([l.strip() for l in SAMPLEXML.splitlines()])
        self.assertEqual(obs_stripped, exp_stripped)

    def test_add_sample_prep(self):
        submission = EBISubmission('001', 'teststudy', 'test asbstract',
                                   'metagenome')
        submission.add_sample('test1')
        submission.add_sample('test2')
        submission.add_sample_prep('test1', 'ILLUMINA', 'fastq',
                                   self.path, 'experiment description',
                                   'library protocol')
        prep_info = submission.samples['test1']['preps'][0]
        self.assertEqual(prep_info['platform'], 'ILLUMINA')
        self.assertEqual(prep_info['file_path'], self.path)
        with self.assertRaises(KeyError):
            submission.add_sample_prep('test3', 'ILLUMINA', 'fastq',
                                       self.path, 'experiment description',
                                       'library protocol')

    def test_generate_library_descriptor(self):
        e = EBISubmission('2', 'Study Title', 'Study Abstract', 'metagenome')
        elm = ET.Element('design', {'foo': 'bar'})

        e._generate_library_descriptor(elm, 'sample', 10, 'libconsprot')
        exp = ''.join([l.strip() for l in GENLIBDESC.splitlines()])
        obs = ET.tostring(elm)
        self.assertEqual(obs, exp)

    def test_generate_spot_descriptor(self):
        e = EBISubmission('2', 'Study Title', 'Study Abstract', 'metagenome')
        elm = ET.Element('design', {'foo': 'bar'})

        e._generate_spot_descriptor(elm, 'LS454')
        exp = ''.join([l.strip() for l in GENSPOTDESC.splitlines()])
        obs = ET.tostring(elm)
        self.assertEqual(obs, exp)

    def test_generate_experiment_xml(self):
        submission = EBISubmission('001', 'teststudy', 'test asbstract',
                                   'metagenome')
        submission.add_sample('test1')
        submission.add_sample_prep('test1', 'ILLUMINA', 'fastq',
                                   'fakepath',
                                   'experiment description',
                                   'library protocol')
        xmlelement = submission.generate_experiment_xml()
        xml = minidom.parseString(ET.tostring(xmlelement))
        xmlstring = xml.toprettyxml(indent='  ', encoding='UTF-8')
        obs_stripped = ''.join([l.strip() for l in xmlstring.splitlines()])
        exp_stripped = ''.join([l.strip() for l in EXPERIMENTXML.splitlines()])
        self.assertEqual(obs_stripped, exp_stripped)

    def test_generate_run_xml(self):
        submission = EBISubmission('001', 'teststudy', 'test asbstract',
                                   'metagenome')
        submission.add_sample('test1')
        submission.add_sample_prep('test1', 'ILLUMINA', 'fastq',
                                   '__init__.py', 'experiment description',
                                   'library protocol')
        xmlelement = submission.generate_run_xml()
        xml = minidom.parseString(ET.tostring(xmlelement))
        xmlstring = xml.toprettyxml(indent='  ', encoding='UTF-8')
        obs_stripped = ''.join([l.strip() for l in xmlstring.splitlines()])
        exp_stripped = ''.join([l.strip() for l in RUNXML.splitlines()])
        self.assertEqual(obs_stripped, exp_stripped)

    def test_generate_submission_xml(self):
        submission = EBISubmission('001', 'teststudy', 'test asbstract',
                                   'metagenome')
        submission.add_sample('test1')
        submission.add_sample_prep('test1', 'ILLUMINA', 'fastq',
                                   '__init__.py', 'experiment description',
                                   'library protocol')
        with self.assertRaises(NoXMLError):
            xmlelement = submission.generate_submission_xml('VALIDATE')
        # add more tests

    def test__write_xml_file(self):
        e = EBISubmission('2', 'Study Title', 'Study Abstract', 'metagenome')
        elm = ET.Element('TESTING', {'foo': 'bar'})
        e._write_xml_file(lambda: elm, 'thing', 'testfile')
        self.assertEqual(e.thing, 'testfile')
        obs = open('testfile').read()
        exp = '<?xml version="1.0" encoding="UTF-8"?>\n<TESTING foo="bar"/>\n'
        self.assertEqual(obs, exp)
        remove('testfile')

    def test_write_study_xml(self):
        submission = EBISubmission('001', 'teststudy', 'test asbstract',
                                   'metagenome')
        fh, output = mkstemp()
        submission.write_study_xml(output)
        close(fh)

        obs_stripped = ''.join([l.strip() for l in open(output)])
        exp_stripped = ''.join([l.strip() for l in STUDYXML.splitlines()])
        self.assertEqual(obs_stripped, exp_stripped)
        remove(output)

    def test_write_sample_xml(self):
        submission = EBISubmission('001', 'teststudy', 'test asbstract',
                                   'metagenome')
        submission.add_sample('test1')
        submission.add_sample('test2')
        fh, output = mkstemp()
        close(fh)
        submission.write_sample_xml(output)

        obs_stripped = ''.join([l.strip() for l in open(output)])
        exp_stripped = ''.join([l.strip() for l in SAMPLEXML.splitlines()])
        self.assertEqual(obs_stripped, exp_stripped)
        remove(output)

    def test_write_experiment_xml(self):
        submission = EBISubmission('001', 'teststudy', 'test asbstract',
                                   'metagenome')
        submission.add_sample('test1')
        submission.add_sample_prep('test1', 'ILLUMINA', 'fastq',
                                   'fakepath', 'experiment description',
                                   'library protocol')
        fh, output = mkstemp()
        close(fh)
        submission.write_experiment_xml(output)
        obs_stripped = ''.join([l.strip() for l in open(output)])
        exp_stripped = ''.join([l.strip() for l in EXPERIMENTXML.splitlines()])
        self.assertEqual(obs_stripped, exp_stripped)
        remove(output)

    def test_write_run_xml(self):
        # This just writes out the output from generate_run_xml...
        pass

    def test_write_submission_xml(self):
        # This just writes out the output from generated_submission_xml...
        pass

    def test_write_all_xml_files(self):
        # This just writes out the output from the generation methods...
        pass

    def test_add_samples_from_templates(self):
        sample_template = StringIO.StringIO(EXP_SAMPLE_TEMPLATE)
        prep_template = StringIO.StringIO(EXP_PREP_TEMPLATE)
        submission = EBISubmission('001', 'teststudy', 'test asbstract',
                                   'metagenome')
        submission.add_samples_from_templates(sample_template, [prep_template],
                                              self.path)
        self.assertTrue('sample1' in submission.samples)
        self.assertTrue('sample2' in submission.samples)
        self.assertTrue('sample3' in submission.samples)
        self.assertEqual(submission.samples['sample2']['preps'][0]['platform'],
                         'ILLUMINA')
        self.assertEqual(
            submission.samples['sample2']['preps'][0]['file_path'],
            self.path + '/sample2.fastq')
        with self.assertRaises(KeyError):
            submission.samples['nothere']

    def test_from_templates_and_demux_fastq(self):
        # sample_template = StringIO.StringIO(EXP_SAMPLE_TEMPLATE)
        # prep_template = StringIO.StringIO(EXP_PREP_TEMPLATE)
        # output = self.path + '/demux_output'
        # submission = EBISubmission.from_templates_and_demux_fastq(
        #     '001', 'study_title', 'study_abstract', 'investigation_type',
        #     sample_template, [prep_template], self.path + '/demux.fastq',
        #     output)
        # remove output dir
        pass

    def test_from_templates_and_per_sample_fastqs(self):
        sample_template = StringIO.StringIO(EXP_SAMPLE_TEMPLATE)
        prep_template = StringIO.StringIO(EXP_PREP_TEMPLATE)
        submission = EBISubmission.from_templates_and_per_sample_fastqs(
            '001', 'test study', 'abstract',
            'type',  sample_template, [prep_template], self.path)
        self.assertEqual(submission.samples['sample2']['preps'][0]['platform'],
                         'ILLUMINA')
        self.assertEqual(
            submission.samples['sample2']['preps'][0]['file_path'],
            self.path + '/sample2.fastq')
        with self.assertRaises(KeyError):
            preps = submission.samples['nothere']


SAMPLEXML = """<?xml version="1.0" encoding="UTF-8"?>
<SAMPLE_SET xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noName\
spaceSchemaLocation="ftp://ftp.sra.ebi.ac.uk/meta/xsd/sra_1_3/SRA.sample.xsd">
  <SAMPLE alias="qiime_study_001:test1" center_name="CCME-COLORADO">
    <TITLE>test1</TITLE>
    <SAMPLE_NAME>
      <TAXON_ID>no_data</TAXON_ID>
    </SAMPLE_NAME>
    <DESCRIPTION>no_data</DESCRIPTION>
  </SAMPLE>
  <SAMPLE alias="qiime_study_001:test2" center_name="CCME-COLORADO">
    <TITLE>test2</TITLE>
    <SAMPLE_NAME>
      <TAXON_ID>no_data</TAXON_ID>
    </SAMPLE_NAME>
    <DESCRIPTION>no_data</DESCRIPTION>
  </SAMPLE>
</SAMPLE_SET>
"""

STUDYXML = """<?xml version="1.0" encoding="UTF-8"?>
<STUDY_SET xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noName\
spaceSchemaLocation="ftp://ftp.sra.ebi.ac.uk/meta/xsd/sra_1_3/SRA.study.xsd">
  <STUDY alias="qiime_study_001" center_name="CCME-COLORADO">
    <DESCRIPTOR>
      <STUDY_TITLE>
        teststudy
      </STUDY_TITLE>
      <STUDY_TYPE existing_study_type="metagenome"/>
      <STUDY_ABSTRACT>
        test asbstract
      </STUDY_ABSTRACT>
    </DESCRIPTOR>
  </STUDY>
</STUDY_SET>
"""

EXPERIMENTXML = """<?xml version="1.0" encoding="UTF-8"?>
<EXPERIMENT_SET xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:no\
NamespaceSchemaLocation="ftp://ftp.sra.ebi.ac.uk/meta/xsd/sra_1_3/SRA.\
experiment.xsd">
  <EXPERIMENT alias="qiime_study_001:test1:0" center_name="CCME-COLORADO">
    <TITLE>qiime_study_001:test1:0</TITLE>
    <STUDY_REF refname="qiime_study_001"/>
    <DESIGN>
      <DESIGN_DESCRIPTION>experiment description</DESIGN_DESCRIPTION>
      <SAMPLE_DESCRIPTOR refname="qiime_study_001:test1"/>
      <LIBRARY_DESCRIPTOR>
        <LIBRARY_NAME>test1:0</LIBRARY_NAME>
        <LIBRARY_STRATEGY>POOLCLONE</LIBRARY_STRATEGY>
        <LIBRARY_SOURCE>METAGENOMIC</LIBRARY_SOURCE>
        <LIBRARY_SELECTION>unspecified</LIBRARY_SELECTION>
        <LIBRARY_LAYOUT>
          <SINGLE/>
        </LIBRARY_LAYOUT>
        <LIBRARY_CONSTRUCTION_PROTOCOL>library protocol</LIBRARY_CONSTRUCTION\
_PROTOCOL>
      </LIBRARY_DESCRIPTOR>
    </DESIGN>
    <PLATFORM>
      <ILLUMINA>
        <INSTRUMENT_MODEL>unspecified</INSTRUMENT_MODEL>
      </ILLUMINA>
    </PLATFORM>
    <EXPERIMENT_ATTRIBUTES>
      <EXPERIMENT_ATTRIBUTE>
        <TAG>experiment_design_description</TAG>
        <VALUE>experiment description</VALUE>
      </EXPERIMENT_ATTRIBUTE>
      <EXPERIMENT_ATTRIBUTE>
        <TAG>file_path</TAG>
        <VALUE>fakepath</VALUE>
      </EXPERIMENT_ATTRIBUTE>
      <EXPERIMENT_ATTRIBUTE>
        <TAG>file_type</TAG>
        <VALUE>fastq</VALUE>
      </EXPERIMENT_ATTRIBUTE>
      <EXPERIMENT_ATTRIBUTE>
        <TAG>library_construction_protocol</TAG>
        <VALUE>library protocol</VALUE>
      </EXPERIMENT_ATTRIBUTE>
      <EXPERIMENT_ATTRIBUTE>
        <TAG>platform</TAG>
        <VALUE>ILLUMINA</VALUE>
      </EXPERIMENT_ATTRIBUTE>
    </EXPERIMENT_ATTRIBUTES>
  </EXPERIMENT>
</EXPERIMENT_SET>
"""

RUNXML = """
<?xml version="1.0" encoding="UTF-8"?>
<RUN_SET xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:no\
NamespaceSchemaLocation="ftp://ftp.sra.ebi.ac.uk/meta/xsd/sra_1_3/SRA.run.xsd">
  <RUN alias="__init__.py_run" center_name="CCME-COLORADO">
    <EXPERIMENT_REF refname="qiime_study_001:test1:0"/>
    <DATA_BLOCK>
      <FILES>
        <FILE checksum="665d8f3b5badd430b48ca2e165bad491" checksum_method=\
"MD5" filename="__init__.py" filetype="fastq" \
quality_scring_system="phred"/>
      </FILES>
    </DATA_BLOCK>
  </RUN>
</RUN_SET>
"""

ADDDICTTEST = """<TESTING foo="bar">
    <foo>
        <TAG>&gt;x</TAG>
        <VALUE>&lt;y</VALUE>
    </foo>
    <foo>
        <TAG>x</TAG>
        <VALUE>y</VALUE>
    </foo>
</TESTING>
"""

GENLIBDESC = """<design foo="bar">
    <LIBRARY_DESCRIPTOR>
        <LIBRARY_NAME>sample:10</LIBRARY_NAME>
        <LIBRARY_STRATEGY>POOLCLONE</LIBRARY_STRATEGY>
        <LIBRARY_SOURCE>METAGENOMIC</LIBRARY_SOURCE>
        <LIBRARY_SELECTION>unspecified</LIBRARY_SELECTION>
        <LIBRARY_LAYOUT><SINGLE /></LIBRARY_LAYOUT>
        <LIBRARY_CONSTRUCTION_PROTOCOL>libconsprot
        </LIBRARY_CONSTRUCTION_PROTOCOL>
    </LIBRARY_DESCRIPTOR>
</design>
"""

GENSPOTDESC = """<design foo="bar">
    <SPOT_DESCRIPTOR>
        <SPOT_DECODE_SPEC />
        <READ_SPEC>
            <READ_INDEX>0</READ_INDEX>
            <READ_CLASS>Application Read</READ_CLASS>
            <READ_TYPE>Forward</READ_TYPE>
            <BASE_COORD>1</BASE_COORD>
        </READ_SPEC>
    </SPOT_DESCRIPTOR>
</design>
"""

EXP_SAMPLE_TEMPLATE = (
    "sample_name\tcollection_timestamp\tdescription\thas_extracted_data\t"
    "has_physical_specimen\thost_subject_id\tlatitude\tlongitude\t"
    "physical_location\trequired_sample_info_status_id\tsample_type\t"
    "str_column\n"
    "sample1\t2014-05-29 12:24:51\tTest Sample 1\tTrue\tTrue\tNotIdentified\t"
    "42.42\t41.41\tlocation1\t1\ttype1\tValue for sample 1\n"
    "sample2\t2014-05-29 12:24:51\t"
    "Test Sample 2\tTrue\tTrue\tNotIdentified\t4.2\t1.1\tlocation1\t1\t"
    "type1\tValue for sample 2\n"
    "sample3\t2014-05-29 12:24:51\tTest Sample 3\tTrue\t"
    "True\tNotIdentified\t4.8\t4.41\tlocation1\t1\ttype1\t"
    "Value for sample 3\n")

EXP_PREP_TEMPLATE = (
    "sample_name\tcenter_name\tcenter_project_name\tdata_type_id\t"
    "temp_status_id\tstr_column\tplatform\texperiment_design_description"
    "\tlibrary_construction_protocol"
    "\nsample1\tANL\tTest Project\t2\t1\tValue for sample 3"
    "\tILLUMINA\texp design\tlib protocol\n"
    "sample2\tANL\tTest Project\t2\t1\tValue for sample 1"
    "\tILLUMINA\texp design\tlib protocol\n"
    "sample3\tANL\tTest Project\t2\t1\tValue for sample 2"
    "\tILLUMINA\texp design\tlib protocol\n")

if __name__ == "__main__":
    main()
