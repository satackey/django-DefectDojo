import hashlib
import logging
import re

from defusedxml import ElementTree

from dojo.models import Finding

from cpe import CPE

logger = logging.getLogger(__name__)

SEVERITY = ['Info', 'Low', 'Medium', 'High', 'Critical']


class DependencyCheckParser(object):
    def get_field_value(self, parent_node, field_name):
        field_node = parent_node.find(self.namespace + field_name)
        field_value = '' if field_node is None else field_node.text
        return field_value

    def get_filename_from_dependency(self, dependency):
        return self.get_field_value(dependency, 'fileName')

    def get_component_name_and_version_from_dependency(self, dependency):
        component_name, component_version = None, None
        # big try catch to avoid crashint the parser on some unexpected stuff
        try:
            identifiers_node = dependency.find(self.namespace + 'identifiers')
            if identifiers_node:
                # <identifiers>
                # 	<identifier type="cpe" confidence="HIGHEST">
                # 		<name>cpe:/a:apache:xalan-java:2.7.1</name>
                # 		<url>https://web.nvd.nist.gov/view/vuln/search-results?adv_search=true&amp;cves=on&amp;cpe_version=cpe%3A%2Fa%3Aapache%3Axalan-java%3A2.7.1</url>
                # 	</identifier>
                # 	<identifier type="maven" confidence="HIGHEST">
                # 		<name>xalan:serializer:2.7.1</name>
                # 		<url>https://search.maven.org/remotecontent?filepath=xalan/serializer/2.7.1/serializer-2.7.1.jar</url>
                # 	</identifier>
                # </identifiers>
                cpe_node = identifiers_node.find('.//' + self.namespace + 'identifier[@type="cpe"]')
                if cpe_node:
                    logger.debug('cpe string: ' + self.get_field_value(cpe_node, 'name'))
                    cpe = CPE(self.get_field_value(cpe_node, 'name'))
                    component_name = cpe.get_vendor()[0] + ':' if len(cpe.get_vendor()) > 0 else ''
                    component_name += cpe.get_product()[0] if len(cpe.get_product()) > 0 else ''
                    component_name = component_name if component_name else None
                    component_version = cpe.get_version()[0] if len(cpe.get_version()) > 0 else None
                    # logger.debug('get_edition: ' + str(cpe.get_edition()))
                    # logger.debug('get_language: ' + str(cpe.get_language()))
                    # logger.debug('get_part: ' + str(cpe.get_part()))
                    # logger.debug('get_software_edition: ' + str(cpe.get_software_edition()))
                    # logger.debug('get_target_hardware: ' + str(cpe.get_target_hardware()))
                    # logger.debug('get_target_software: ' + str(cpe.get_target_software()))
                    # logger.debug('get_vendor: ' + str(cpe.get_vendor()))
                    # logger.debug('get_update: ' + str(cpe.get_update()))
                else:
                    maven_node = identifiers_node.find('.//' + self.namespace + 'identifier[@type="maven"]')
                    if maven_node:
                        # logger.debug('maven_string: ' + self.get_field_value(maven_node, 'name'))
                        maven_parts = self.get_field_value(maven_node, 'name').split(':')
                        # logger.debug('maven_parts:' + str(maven_parts))
                        if len(maven_parts) == 3:
                            component_name = maven_parts[0] + ':' + maven_parts[1]
                            component_version = maven_parts[2]
            else:
                evidence_collected_node = dependency.find(self.namespace + 'evidenceCollected')
                if evidence_collected_node:
                    # <evidenceCollected>
                    # <evidence type="product" confidence="HIGH">
                    # 	<source>file</source>
                    # 	<name>name</name>
                    # 	<value>jquery</value>
                    # </evidence>
                    # <evidence type="version" confidence="HIGH">
                    # 	<source>file</source>
                    # 	<name>version</name>
                    # 	<value>3.1.1</value>
                    # </evidence>'
                    product_node = evidence_collected_node.find('.//' + self.namespace + 'evidence[@type="product"]')
                    if product_node:
                        component_name = self.get_field_value(product_node, 'value')
                        version_node = evidence_collected_node.find('.//' + self.namespace + 'evidence[@type="version"]')
                        if version_node:
                            component_version = self.get_field_value(version_node, 'value')

            # logger.debug('returning name/version: %s %s', component_name, component_version)
        except:
            logger.exception('error parsing component_name and component_version')
            logger.debug('dependency: %s', ElementTree.tostring(dependency, encoding='utf8', method='xml'))

        return component_name, component_version

    def get_finding_from_vulnerability(self, dependency, vulnerability, test):
        dependency_filename = self.get_filename_from_dependency(dependency)
        # logger.debug('dependency_filename: %s', dependency_filename)

        name = self.get_field_value(vulnerability, 'name')
        cwes_node = vulnerability.find(self.namespace + 'cwes')
        if cwes_node is not None:
            cwe_field = self.get_field_value(cwes_node, 'cwe')
        else:
            cwe_field = self.get_field_value(vulnerability, 'cwe')
        description = self.get_field_value(vulnerability, 'description')

        title = '{0} | {1}'.format(dependency_filename, name)
        cve = name[:28]
        if cve and not cve.startswith('CVE'):
            # for vulnerability sources which have a CVE, it is the start of the 'name'.
            # for other sources, we have to set it to None
            cve = None

        # Use CWE-1035 as fallback
        cwe = 1035  # Vulnerable Third Party Component
        if cwe_field:
            m = re.match(r"^(CWE-)?(\d+)", cwe_field)
            if m:
                cwe = int(m.group(2))
        cvssv2_node = vulnerability.find(self.namespace + 'cvssV2')
        cvssv3_node = vulnerability.find(self.namespace + 'cvssV3')
        if cvssv3_node is not None:
            severity = self.get_field_value(cvssv3_node, 'baseSeverity').lower().capitalize()
        elif cvssv2_node is not None:
            severity = self.get_field_value(cvssv2_node, 'severity').lower().capitalize()
        else:
            severity = self.get_field_value(vulnerability, 'severity').lower().capitalize()
        # logger.debug("severity: " + severity)
        if severity in SEVERITY:
            severity = severity
        else:
            tag = "Severity is inaccurate : " + str(severity)
            title += " | " + tag
            logger.warn("Warning: Inaccurate severity detected. Setting it's severity to Medium level.\n" + "Title is :" + title)
            severity = "Medium"

        reference_detail = None
        references_node = vulnerability.find(self.namespace + 'references')

        if references_node is not None:
            reference_detail = ''
            for reference_node in references_node.findall(self.namespace +
                                                          'reference'):
                name = self.get_field_value(reference_node, 'name')
                source = self.get_field_value(reference_node, 'source')
                url = self.get_field_value(reference_node, 'url')
                reference_detail += 'name: {0}\n' \
                                     'source: {1}\n' \
                                     'url: {2}\n\n'.format(name, source, url)

        component_name, component_version = self.get_component_name_and_version_from_dependency(dependency)

        return Finding(
            title=title,
            file_path=dependency_filename,
            test=test,
            cwe=cwe,
            cve=cve,
            active=False,
            verified=False,
            description=description,
            severity=severity,
            numerical_severity=Finding.get_numerical_severity(severity),
            static_finding=True,
            references=reference_detail,
            component_name=component_name,
            component_version=component_version)

    def __init__(self, filename, test):
        self.dupes = dict()
        self.items = ()
        self.namespace = ''

        if filename is None:
            return

        content = filename.read()

        if content is None:
            return

        scan = ElementTree.fromstring(content)
        regex = r"{.*}"
        matches = re.match(regex, scan.tag)
        try:
            self.namespace = matches.group(0)
        except:
            self.namespace = ""

        dependencies = scan.find(self.namespace + 'dependencies')

        if dependencies:
            for dependency in dependencies.findall(self.namespace +
                                                   'dependency'):
                vulnerabilities = dependency.find(self.namespace +
                                                  'vulnerabilities')
                if vulnerabilities is not None:
                    for vulnerability in vulnerabilities.findall(
                            self.namespace + 'vulnerability'):
                        finding = self.get_finding_from_vulnerability(dependency,
                            vulnerability, test)

                        if finding is not None:
                            key_str = '{}|{}|{}'.format(finding.severity,
                                                         finding.title,
                                                         finding.description)
                            key = hashlib.md5(key_str.encode('utf-8')).hexdigest()

                            if key not in self.dupes:
                                self.dupes[key] = finding

        self.items = list(self.dupes.values())
