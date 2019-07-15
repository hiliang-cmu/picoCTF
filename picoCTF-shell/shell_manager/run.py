#!/usr/bin/env python3
"""
Shell Manager -- Tools for deploying and packaging problems.
"""

import logging
from argparse import ArgumentParser

import coloredlogs
from hacksport.install import install_problems, install_bundle, uninstall_bundle
from hacksport.deploy import deploy_problems, undeploy_problems
from hacksport.status import clean, publish, status
from shell_manager.config import (print_configuration,
                                  set_configuration_option)
from shell_manager.util import (FatalException, get_hacksports_config,
                                place_default_config)

coloredlogs.DEFAULT_LOG_FORMAT = "%(asctime)s %(name)s %(levelname)s: %(message)s"
coloredlogs.DEFAULT_DATE_FORMAT = "%H:%M:%S"

logger = logging.getLogger(__name__)


def main():
    parser = ArgumentParser(description="Shell Manager")
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        default=False,
        help="show debug information")
    parser.add_argument(
        "--colorize",
        default="auto",
        choices=["auto", "never"],
        help="support colored output")
    subparsers = parser.add_subparsers()

    deploy_parser = subparsers.add_parser("deploy", help="problem deployment")
    deploy_parser.add_argument(
        "-n",
        "--num-instances",
        type=int,
        default=1,
        help="number of instances to generate (numbers 0 through n-1).")
    deploy_parser.add_argument(
        "-i",
        "--instances",
        action="append",
        type=int,
        help="particular instance(s) to generate.")
    deploy_parser.add_argument(
        "-d",
        "--dry",
        action="store_true",
        help="don't make persistent changes.")
    deploy_parser.add_argument(
        "-r",
        "--redeploy",
        action="store_true",
        help="redeploy instances that have already been deployed")
    deploy_parser.add_argument(
        "-nr",
        "--no-restart",
        action="store_true",
        help="do not restart xinetd after deployment.")
    deploy_parser.add_argument(
        "problem_paths", nargs="*", type=str, help="paths to problems.")
    deploy_parser.set_defaults(func=deploy_problems)

    install_parser = subparsers.add_parser(
        "install", help="problem installation")
    install_parser.add_argument(
        "problem_paths", nargs="*", type=str,
        help="paths to problem source directories")
    install_parser.set_defaults(func=install_problems)

    install_bundle_parser = subparsers.add_parser("install-bundle",
                                                  help="bundle installation")
    install_bundle_parser.add_argument(
        "bundle_path", type=str, help="path to bundle file")
    install_bundle_parser.set_defaults(func=install_bundle)

    uninstall_bundle_parser = subparsers.add_parser("uninstall-bundle",
                                                    help="bundle removal")
    uninstall_bundle_parser.add_argument(
        "bundle_name", type=str, help="name of installed bundle")
    uninstall_bundle_parser.set_defaults(func=uninstall_bundle)

    # undeploy_parser = subparsers.add_parser(
    #     "undeploy",
    #     help=
    #     "problem undeployment. cannot guarantee full removal of problem files")
    # undeploy_parser.add_argument(
    #     "-n",
    #     "--num-instances",
    #     type=int,
    #     default=1,
    #     help="number of instances to undeploy (numbers 0 through n-1).")
    # undeploy_parser.add_argument(
    #     "-i",
    #     "--instances",
    #     action="append",
    #     type=int,
    #     help="particular instance(s) to generate.")
    # undeploy_parser.add_argument(
    #     "-b",
    #     "--bundle",
    #     action="store_true",
    #     help="specify a bundle of problems to undeploy.")
    # undeploy_parser.add_argument(
    #     "problem_paths", nargs="*", type=str, help="paths to problems.")
    # undeploy_parser.set_defaults(func=undeploy_problems)

    clean_parser = subparsers.add_parser(
        "clean",
        help="Clean up the intermediate staging data stored during deployments")
    clean_parser.set_defaults(func=clean)

    status_parser = subparsers.add_parser(
        "status",
        help=
        "List the installed problems and bundles and any instances associated with them."
    )
    status_parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Show information about all problem instanes.")
    status_parser.add_argument(
        "-p",
        "--problem",
        type=str,
        default=None,
        help="Display status information for a given problem.")
    status_parser.add_argument(
        "-b",
        "--bundle",
        type=str,
        default=None,
        help="Display status information for a given bundle.")
    status_parser.add_argument(
        "-j",
        "--json",
        action="store_true",
        default=None,
        help="Display status information in json format")
    status_parser.add_argument(
        "-e",
        "--errors-only",
        action="store_true",
        help="Only print problems with failing service status.")
    status_parser.set_defaults(func=status)

    publish_parser = subparsers.add_parser(
        "publish",
        help=
        "Generate the information needed by the web server for this deployment."
    )
    publish_parser.set_defaults(func=publish)

    config_parser = subparsers.add_parser(
        "config", help="View or modify configuration options")
    config_parser.add_argument(
        "-f",
        "--file",
        type=str,
        default=None,
        help=
        "Which configuration file to access. If none is provided, the system wide configuration file will be used."
    )
    config_parser.add_argument(
        "-j",
        "--json",
        action="store_true",
        default=False,
        help=
        "Whether to display the configuration options in JSON form or pretty printed. Defaults to False."
    )
    config_parser.set_defaults(func=print_configuration)
    config_subparsers = config_parser.add_subparsers()

    config_set_parser = config_subparsers.add_parser(
        "set", help="Set configuration options")
    config_set_parser.add_argument(
        "-f", "--field", type=str, required=True, help="which field to set")
    config_set_parser.add_argument(
        "-v", "--value", type=str, required=True, help="options's new value")
    config_set_parser.add_argument(
        "-j",
        "--json",
        action="store_true",
        default=False,
        help="interpret the given value as JSON")
    config_set_parser.add_argument(
        "--allow-type-change",
        action="store_true",
        default=False,
        help="Allow the supplied field to change types if already specified")
    config_set_parser.set_defaults(func=set_configuration_option)

    args = parser.parse_args()

    if args.colorize == "never":
        coloredlogs.DEFAULT_LEVEL_STYLES = {}
        coloredlogs.DEFAULT_FIELD_STYLES = {}

    coloredlogs.install()

    if args.debug:
        coloredlogs.set_level(logging.DEBUG)
    try:
        try:
            config = get_hacksports_config()
        except PermissionError:
            logger.error("You must run shell_manager with sudo.")
            raise FatalException
        except FileNotFoundError:
            place_default_config()
            logger.info(
                "There was no default configuration. One has been created for you. Please edit it accordingly using the 'shell_manager config' subcommand before deploying any instances."
            )
            raise FatalException

        # Call the default function
        if "func" in args:
            args.func(args, config)
        else:
            parser.print_help()
    except FatalException:
        exit(1)


if __name__ == "__main__":
    main()
