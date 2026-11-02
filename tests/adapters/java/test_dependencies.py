import textwrap

from inspect4all.adapters.java.dependencies import JavaDependencyExtractor

POM_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <project xmlns="http://maven.apache.org/POM/4.0.0">
      <groupId>com.example</groupId>
      <artifactId>myapp</artifactId>
      <version>1.0.0</version>
      <dependencies>
        <dependency>
          <groupId>org.springframework</groupId>
          <artifactId>spring-core</artifactId>
          <version>5.3.0</version>
        </dependency>
        <dependency>
          <groupId>junit</groupId>
          <artifactId>junit</artifactId>
          <version>4.13</version>
          <scope>test</scope>
        </dependency>
      </dependencies>
    </project>
""")


def test_extract_maven_deps(tmp_path):
    pom = tmp_path / "pom.xml"
    pom.write_text(POM_XML, encoding="utf-8")
    deps = JavaDependencyExtractor().extract(tmp_path)
    names = [d.name for d in deps]
    assert any("spring-core" in n or "spring" in n.lower() for n in names)


def test_extract_no_build_file(tmp_path):
    deps = JavaDependencyExtractor().extract(tmp_path)
    assert deps == []
