# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from textwrap import dedent

from fixtures import FakeLogger
from fixtures import Fixture
from fixtures import MonkeyPatch
from fixtures import TempDir
import mox
from testtools import TestCase

from bindep.depends import Depends
from bindep.main import main


class MainFixture(Fixture):
    """Encapsulate running main().

    :attr logger: The logger fixture from the process invocation.
    :attr path: The path to the root of the isolated temp dir.
    """

    def setUp(self):
        super(MainFixture, self).setUp()
        self.logger = self.useFixture(FakeLogger())
        self.path = self.useFixture(TempDir()).path
        self.addCleanup(os.chdir, self.path)
        os.chdir(self.path)


class TestMain(TestCase):

    def test_profiles_lists_profiles(self):
        logger = self.useFixture(FakeLogger())
        self.useFixture(MonkeyPatch('sys.argv', ['bindep', '--profiles']))

        class TestFactory:
            def platform_profiles(self):
                return ['platform:ubuntu', 'platform:i386']

            def profiles(self):
                return ['bar', 'foo']
        self.assertEqual(0, main(depends=TestFactory()))
        self.assertEqual(dedent("""\
            Platform profiles:
            platform:ubuntu
            platform:i386

            Configuration profiles:
            bar
            foo
            """), logger.output)

    def test_missing_requirements_file(self):
        fixture = self.useFixture(MainFixture())
        self.useFixture(MonkeyPatch('sys.argv', ['bindep']))
        self.assertEqual(1, main())
        self.assertEqual(
            'No other-requirements.txt file found.\n', fixture.logger.output)

    def test_empty_requirements_file(self):
        fixture = self.useFixture(MainFixture())
        self.useFixture(MonkeyPatch('sys.argv', ['bindep']))
        with open(fixture.path + '/other-requirements.txt', 'wt'):
            pass
        self.assertEqual(0, main())
        self.assertEqual('', fixture.logger.output)

    def test_specific_profile(self):
        logger = self.useFixture(FakeLogger())
        self.useFixture(MonkeyPatch('sys.argv', ['bindep', 'myprofile']))
        mocker = mox.Mox()
        depends = mocker.CreateMock(Depends)
        depends.platform_profiles().AndReturn(["platform:ubuntu"])
        depends.active_rules(["myprofile", "platform:ubuntu"]).AndReturn([""])
        depends.check_rules([""]).AndReturn([])
        mocker.ReplayAll()
        self.assertEqual(0, main(depends=depends))
        self.assertEqual("", logger.output)
        self.addCleanup(mocker.VerifyAll)
        self.addCleanup(mocker.UnsetStubs)

    def test_default_profile(self):
        logger = self.useFixture(FakeLogger())
        self.useFixture(MonkeyPatch('sys.argv', ['bindep']))
        mocker = mox.Mox()
        depends = mocker.CreateMock(Depends)
        depends.platform_profiles().AndReturn(["platform:ubuntu"])
        depends.active_rules(["default", "platform:ubuntu"]).AndReturn(["A"])
        depends.check_rules(["A"]).AndReturn([])
        mocker.ReplayAll()
        self.assertEqual(0, main(depends=depends))
        self.assertEqual("", logger.output)
        self.addCleanup(mocker.VerifyAll)
        self.addCleanup(mocker.UnsetStubs)

    def test_errors_shown(self):
        logger = self.useFixture(FakeLogger())
        self.useFixture(MonkeyPatch('sys.argv', ['bindep']))
        mocker = mox.Mox()
        depends = mocker.CreateMock(Depends)
        depends.platform_profiles().AndReturn([])
        depends.active_rules(["default"]).AndReturn([])
        depends.check_rules([]).AndReturn(
            [('missing', ['foo', 'bar']),
             ('badversion', [('quux', '<=12', '13'), ('qaaz', '!=10', '10')])])
        mocker.ReplayAll()
        self.assertEqual(1, main(depends=depends))
        self.assertEqual(dedent("""\
            Missing packages:
                foo bar
            Bad versions of installed packages:
                quux version 13 does not match <=12
                qaaz version 10 does not match !=10
            """), logger.output)
        self.addCleanup(mocker.VerifyAll)
        self.addCleanup(mocker.UnsetStubs)

