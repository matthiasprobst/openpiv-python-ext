import pathlib
from importlib.metadata import version
from uuid import uuid4

import ontolutils
import rdflib
import requests.exceptions
from ontolutils import merge_jsonld, QUDT_UNIT
from pivmetalib import pivmeta, sd
from pivmetalib.m4i import Method, NumericalVariable
from ssnolib.pimsii import Variable
from ssnolib import m4i

from .settings import PIVSettings

__this_dir__ = pathlib.Path(__file__).parent


def _generate_local_id(base: str = "https://example.org/"):
    """Generate a local ID for the metadata."""
    return f"{base}{uuid4()}"


def save_metadata(setting: PIVSettings, filename: str) -> str:
    """Save the PIV settings to a file."""
    codemeta_filename = __this_dir__ / "../codemeta.json"
    if not codemeta_filename.exists():
        raise FileNotFoundError(f"Codemeta file not found: {codemeta_filename}")

    try:
        software_source_code = sd.SourceCode.from_codemeta(codemeta_filename)
    except requests.exceptions.ConnectionError:
        openpiv_version = version('openpiv')
        software_source_code = sd.SourceCode(
            id="https://doi.org/10.5281/zenodo.5009150",  # zenodo-doi for OpenPIV
            codeRepository="https://github.com/OpenPIV/openpiv-python",
            version=openpiv_version,
            name='OpenPIV',
            description="OpenPIV consists in a Python and Cython modules for scripting and executing the analysis of a set of PIV image pairs. In addition, a Qt and Tk graphical user interfaces are in development, to ease the use for those users who don't have python skills."
        )
    with ontolutils.set_config(blank_node_prefix_name="ex:"):
        software = pivmeta.PIVSoftware(
            hasSourceCode=software_source_code
        )

        corr_method = pivmeta.CorrelationMethod(
            label=setting.correlation_method,
            hasWindowWeightingFunction="none",
            parameter=[
                NumericalVariable(
                    label="normalized correlation",
                    hasUnit=QUDT_UNIT.UNITLESS,
                    value=int(setting.normalized_correlation)
                )
            ]
        )

        sig2noise_method = Method(
            label="Signal to Noise Method",
            parameter=[
                NumericalVariable(
                    label="sig2noise mask",
                    hasUnit=QUDT_UNIT.UNITLESS,
                    value=setting.sig2noise_mask,
                ),
                NumericalVariable(
                    label="sig2noise threshold",
                    hasUnit=QUDT_UNIT.UNITLESS,
                    value=setting.sig2noise_threshold,
                ),
                Variable(
                    label="sig2noise validate",
                    hasUnit=QUDT_UNIT.UNITLESS,
                    value=setting.sig2noise_validate,
                ),
                NumericalVariable(
                    label="sig2noise first pass",
                    hasUnit=QUDT_UNIT.UNITLESS,
                    value=int(setting.validation_first_pass),
                )
            ]
        )

        filter_method = Method(
            label="Local Mean Filter Method",
            parameter=[
                NumericalVariable(
                    label="max filter iteration",
                    hasUnit=QUDT_UNIT.UNITLESS,
                    value=setting.max_filter_iteration
                ),
                NumericalVariable(
                    label="filter kernel size",
                    hasUnit=QUDT_UNIT.PIXEL,
                    value=setting.filter_kernel_size
                )
            ]
        )

        if setting.dynamic_masking_method is not None:
            masking = Method(
                label="Masking Method",
                parameter=[
                    NumericalVariable(
                        label="dynamic masking method",
                        hasUnit=QUDT_UNIT.PIXEL,
                        value=setting.dynamic_masking_threshold
                    ),
                    NumericalVariable(
                        label="dynamic masking filter size",
                        hasUnit=QUDT_UNIT.PIXEL,
                        value=setting.dynamic_masking_filter_size
                    )
                ]
            )

        multi_grid = pivmeta.Multigrid(
            parameter=[
                m4i.NumericalVariable(
                    label="initial interrogation window size",
                    hasUnit=QUDT_UNIT.PIXEL,
                    value=setting.windowsizes[0],
                ),
                m4i.NumericalVariable(
                    label="final interrogation window size",
                    hasUnit=QUDT_UNIT.PIXEL,
                    value=setting.windowsizes[-1]
                ),
                m4i.NumericalVariable(
                    label="initial interrogation window overlap",
                    hasUnit=QUDT_UNIT.PIXEL,
                    value=setting.overlap[0]
                ),
                m4i.NumericalVariable(
                    label="final interrogation window overlap",
                    hasUnit=QUDT_UNIT.PIXEL,
                    value=setting.overlap[-1]
                ),
                m4i.NumericalVariable(
                    label="number of multigrid iterations",
                    hasUnit=QUDT_UNIT.UNITLESS,
                    value=setting.num_iterations
                )
            ]
        )

        piv_evaluation = pivmeta.PIVEvaluation(
            hasEmployedTool=software,
            realizesMethod=[
                multi_grid,
                corr_method,
                sig2noise_method,
                filter_method,
            ]
        )
        if setting.dynamic_masking_method is not None:
            piv_evaluation.realizesMethod.append(masking)

        virtual_setup = pivmeta.VirtualSetup(
            usesSoftware=software
        )

        # combine both JSON-LD representations:
        merged_json = merge_jsonld([piv_evaluation.model_dump_jsonld(),
                                    virtual_setup.model_dump_jsonld()])

        g = rdflib.Graph()
        g.parse(data=merged_json, format='json-ld')
        ttl = g.serialize(format='ttl')
        with open(filename, 'w') as f:
            f.write("@prefix ex: <https://example.org/> .\n")
            f.write(ttl)

    return filename
    #
    # dt = setting.dt
    #
    # with open(filename, 'w') as f:
    #     f.write("# PIV Settings Metadata\n")
    #     for key, value in setting.__dict__.items():
    #         if isinstance(value, (list, tuple)):
    #             value = ', '.join(map(str, value))
    #         f.write(f"{key}: {value}\n")
