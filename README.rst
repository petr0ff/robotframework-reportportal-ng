robotframework-reportportal-ng
==============================

|Build Status|

Short Description
-----------------

Robot Framework listener module for integration with Report Portal.

Installation
------------

::

    pip install robotframework-reportportal-ng

Usage
-----

This listener requires specified robot framework context variables to be
set up. Some of them are required for execution and some are not.

Parameters list:

::

        RP_UUID - unique id of user in Report Portal profile..
        RP_ENDPOINT - <protocol><hostname>:<port> for connection with Report Portal.
                      Example: http://reportportal.local:8080/
        RP_LAUNCH - name of launch to be used in Report Portal.
        RP_PROJECT - project name for new launches.
        RP_LAUNCH_DOC - documentation of new launch.
        RP_LAUNCH_TAGS - additional tags to mark new launch.

Examples
--------

Using `Pybot`
`````````````

Example command to run test using `Pybot` with report portal listener.

.. code:: bash

    pybot --listener reportportal_listener --escape quot:Q \
    --variable RP_ENDPOINT:http://reportportal.local:8080 \
    --variable RP_UUID:73628339-c4cd-4319-ac5e-6984d3340a41 \
    --variable RP_LAUNCH:"Demo Tests" \
    --variable RP_PROJECT:DEMO_USER_PERSONAL test_folder

Using `Pabot`
`````````````

To run your tests with the listener using pabot, you need to specify prevously created from outuse launch id through its arguments. 

This so because of the specific Robot Framework architecture. Pabot separates your test suite on multiple tests and runs it in separate processes of `pybot`. 

Meanwhile, pybot has its own separate global state and it is absolutely not connected with the other instances of pybot being ran by pabot.

When test execution ends, some of those threads must close Report Portal launch, but because pabot parallelism is not based on the native python threads, there is no any option to choose which one and only thread must close the Report Portal launch.

To solve this problem, report portal listener has its own launch id argument. 

You create a launch from the outside of the listener and close it there and thus it guarantees that the launch was created and will be closed at 100%.

Example usage with the launch id argument:

.. code:: basj

    pybot --listener reportportal_listener:1234567 --variable etc. ...

Where 1234567 is a special launch id value, taken from the response of Report Portal API. 

Example script, how to obtain a launch id:

.. code:: python

      import argparse
      import os
      import re

      import requests
      from invoke import task
      from reportportal_client.service import ReportPortalService

      from helper import command_call, tc_message, current_dir, tc_log, tc_set_build_status
      from reportportal_listener.service import timestamp

      def run__tests(additional_params, report_portal_params=None):
          """Run tests.

          Args:
              additional_params: additional parameters.
              report_portal_params (list): parameters of report portal.

          Returns:
              tests results.
          """
          with tc_log('Run  tests'):
              pabot = ["pabot",
                       "--pabotlib",
                       "--processes", "10",
                       "--outputdir", output_dir(),
                       "--reporttitle", " TEST REPORT",
                       "--log", "log.html",
                       "--report", "report.html",
                       "--output", "output.xml",
                       "--xunit", "xunit.xml",
                       "--xunitskipnoncritical",
                       "--exclude", "develop",
                       "--exclude", "selftest",
                       "--reportbackground", "white:white:white",
                       "--noncritical", "noncritical",
                       "--randomize", "suites",
                       "--consolewidth", "150",
                       "--removekeywords", "WUKS",
                       "--removekeywords", "FOR",
                       "--tagstatexclude", "testrailid=*"
                       ]  # yapf: disable
              
              # Extending with report portal parameters
              if report_portal_params:
                  pabot.extend(report_portal_params)
            
              pabot.append("test")
              result = command_call(pabot, env=environment_variables())
              remove_duplicated_messages(output_dir(), pabot)
              return result



      def _rp_register_launch(rp_service_instance, rp_launch_name, rp_launch_doc="", rp_launch_tags=""):
          """Register new launch using report portal HTTP API.

          Args:
              rp_service_instance (ReportPortalService): Report Portal Robot Service instance.
              rp_launch_name: Launch name to be registered in Report Portal to serve logs from test run.
              rp_launch_doc: Additional information to be set up under RP launch.
              rp_launch_tags: comma separated tags for launch.
          Returns:
              str: Report Portal Launch ID or it silently returns None if any error occurs.
          """
          with tc_log("Register Report Portal Launch"):
              new_launch_id = None
              try:
                  new_launch_id = rp_service_instance.start_launch(name=rp_launch_name, start_time=timestamp(),
                                                                   description=rp_launch_doc, tags=rp_launch_tags.split(','),
                                                                   mode='DEFAULT')
                  tc_message("New Report Portal launch id: {}".format(new_launch_id))
              except Exception as e:
                  tc_message("Report Portal launch was not created due to issue:", status='WARNING')
                  tc_message(e, status='WARNING')
              return new_launch_id


      def _rp_close_launch(rp_service_instance):
          """Close Report Portal launch.

          Args:
              rp_service_instance (ReportPortalService): Report Portal Robot Service instance.
          """
          with tc_log("Closing Report Portal Launch"):
              rp_service_instance.finish_launch(end_time=timestamp(), status=None)
              tc_message("Report Portal Launch is closed")


      def parse_arguments():
          """Parse passed arguments using argument parser.

          Returns:
              Object with parsed arguments.
          """
          parser = argparse.ArgumentParser(description='Prepare server')

          # register additional parameters for Report Portal integration
          parser.add_argument('--rp_endpoint', action="store", dest='rp_endpoint', default=None,
                              help="Endpoint of Report Portal. E.g.: http://reportportalhost.ru:8080")
          parser.add_argument('--rp_project', action="store", dest='rp_project', default=None,
                              help="Project name of Report Portal.")
          parser.add_argument('--rp_uuid', action="store", dest='rp_uuid', default=None,
                              help="Unique identifier of user to log data in Report Portal.")
          parser.add_argument('--rp_launch_doc', action="store", dest='rp_launch_doc', default=None,
                              help="Launch description in Report Portal. E.g.: you can paste here link to teamcity build.")
          parser.add_argument('--rp_launch_tags', action="store", dest='rp_launch_tags', default=None,
                              help="Launch additional tags to filter launches in Report Portal.")
          parser.add_argument('--rp_launch_name', action="store", dest='rp_launch_name', default=None,
                              help="Report name of Report Portal.")

          return parser.parse_args()


      def run__tests_with_report_portal(args):
          """Run tests with report portal integration.

          This function creates a new launch in Report Portal and
          passes it into the test runner method.

          Args:
              args: parsed arguments using argparse.

          Returns:
              Exit code as an execution result of test run script.
          """
          # init report portal service to create new launch
          rp_service = ReportPortalService(endpoint=args.rp_endpoint, project=args.rp_project, token=args.rp_uuid)
          # register new launch to serve test results
          launch_name = args.rp_launch_name or " TEST REPORT"
          launch_id = _rp_register_launch(rp_service_instance=rp_service, rp_launch_name=launch_name,
                                          rp_launch_doc=args.rp_launch_doc, rp_launch_tags=args.rp_launch_tags)
          # register params to pass
          rp_params = [
              '--listener', 'reportportal_listener:{launch_id}'.format(launch_id=launch_id),
              '--variable', 'RP_ENDPOINT:{rp_endpoint}'.format(rp_endpoint=args.rp_endpoint),
              '--variable', 'RP_UUID:{rp_uuid}'.format(rp_uuid=args.rp_uuid),
              '--variable', 'RP_LAUNCH:\'{rp_launch_name}\''.format(rp_launch_name=launch_name),
              '--variable', 'RP_PROJECT:{rp_project}'.format(rp_project=args.rp_project),
              '--variable', 'RP_LAUNCH_TAGS:{rp_launch_tags}'.format(rp_launch_tags=args.rp_launch_tags),
              '--variable', 'RP_LAUNCH_DOC:\'{rp_launch_doc}\''.format(rp_launch_doc=args.rp_launch_doc),
          ]  # yapf: disable
          # run pabot execution with parameters of report portal integration
          rt_code = run__tests(args.additional_params, rp_params)
          # close report portal launch after script ends up with running tests
          _rp_close_launch(rp_service_instance=rp_service)
          return rt_code


      def main(args):
          """Script entry point.

          Args:
              args: parsed arguments using argparse.
          """
          # If Report Portal endpoint parameter is provided
          if args.rp_endpoint:
              # checking if Report Portal is available
              rp_resp = requests.head(args.rp_endpoint)
              if rp_resp.ok:
                  rt_code = run__tests_with_report_portal(args)
              else:
                  error_msg = 'Report Portal is not available. Error: {code} {reason}'.format(
                      code=rp_resp.status_code, reason=rp_resp.reason)


          exit(rt_code)


      @task
      def test(ctx, rp_endpoint=None, additional_params=None, rp_uuid=None, rp_launch_doc=None, rp_launch_tags=None,
               rp_project=None, rp_launch_name=None):
          """Invoke task to run test.

          Args:
              ctx: invoke context.
              additional_params: Additional params to pass
              to robot framework launcher.
              rp_endpoint: Endpoint of Report Portal.
              rp_uuid: Unique identifier of user to log data in Report Portal.
              rp_launch_doc: Launch description in Report Portal.
              rp_launch_tags: Launch additional tags to filter launches in
              Report Portal.
              rp_project: Project name of Report Portal.
              rp_launch_name: Report name of Report Portal.
          """
          args = argparse.Namespace()
          args.additional_params = additional_params
          args.rp_endpoint = rp_endpoint
          args.rp_project = rp_project
          args.rp_uuid = rp_uuid
          args.rp_launch_doc = rp_launch_doc
          args.rp_launch_tags = rp_launch_tags
          args.rp_launch_name = rp_launch_name
          main(args)


      if __name__ == "__main__":
          arguments = parse_arguments()
          main(arguments)


License
-------

Apache License 2.0

.. |Build Status| image:: https://travis-ci.org/ailjushkin/robotframework-reportportal-ng.svg?branch=master
   :target: https://travis-ci.org/ailjushkin/robotframework-reportportal-ng
