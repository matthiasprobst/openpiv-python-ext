import pathlib
from importlib.metadata import version
from typing import Union

import rdflib
import requests.exceptions
from ontolutils import merge_jsonld, QUDT_UNIT
from pivmetalib import pivmeta, sd
from pivmetalib.m4i import Method, NumericalVariable
from pydantic import HttpUrl
from ssnolib import m4i
from ssnolib.pimsii import Variable

from .settings import PIVSettings

__this_dir__ = pathlib.Path(__file__).parent


def save_metadata(setting: PIVSettings, filename: Union[str, pathlib.Path], base_uri: str) -> pathlib.Path:
    """Save the PIV settings to a file.

    Parameters
    ----------
    setting: PIVSettings
        The PIV settings to save
    filename: str
        The filename to save the metadata to
    base_uri: str
        The base URI to use for the metadata. Must be unique for this metadata file. This is important, because
        the IDs for the contained objects built from this base URI, hence another metadata file with the same base URI
        would produce the same IDs, which is not expected. We generate IDs like this in order not to use blank nodes
        and to be able to generate metadata files deterministically.
    """
    filename = pathlib.Path(filename)
    fmt = filename.suffix.strip(".")
    if fmt == "jsonld":
        fmt = "json-ld"

    base_uri = str(HttpUrl(base_uri))
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

    software = pivmeta.PIVSoftware(
        id=f"{base_uri}#PIVSoftware/openpiv",
        hasSourceCode=software_source_code
    )

    corr_method = pivmeta.CorrelationMethod(
        label=setting.correlation_method,
        hasWindowWeightingFunction="none",
        parameter=[
            NumericalVariable(
                id=f"{base_uri}#CorrelationMethod/normalized_correlation",
                label="normalized correlation",
                hasUnit=QUDT_UNIT.UNITLESS,
                has_value=int(setting.normalized_correlation)
            )
        ]
    )

    sig2noise_method = Method(
        label="Signal to Noise Method",
        parameter=[
            NumericalVariable(
                id=f"{base_uri}#SignalToNoiseMethod/sig2noise_mask",
                label="sig2noise mask",
                hasUnit=QUDT_UNIT.UNITLESS,
                has_value=setting.sig2noise_mask,
            ),
            NumericalVariable(
                id=f"{base_uri}#SignalToNoiseMethod/sig2noise_threshold",
                label="sig2noise threshold",
                hasUnit=QUDT_UNIT.UNITLESS,
                has_value=setting.sig2noise_threshold,
            ),
            Variable(
                id=f"{base_uri}#SignalToNoiseMethod/sig2noise_validate",
                label="sig2noise validate",
                hasUnit=QUDT_UNIT.UNITLESS,
                has_value=setting.sig2noise_validate,
            ),
            NumericalVariable(
                id=f"{base_uri}#SignalToNoiseMethod/validation_first_pass",
                label="sig2noise first pass",
                hasUnit=QUDT_UNIT.UNITLESS,
                has_value=int(setting.validation_first_pass),
            )
        ]
    )

    filter_method = Method(
        label="Local Mean Filter Method",
        parameter=[
            NumericalVariable(
                id=f"{base_uri}#LocalMeanFilterMethod/max_filter_iteration",
                label="max filter iteration",
                hasUnit=QUDT_UNIT.UNITLESS,
                has_value=setting.max_filter_iteration
            ),
            NumericalVariable(
                id=f"{base_uri}#LocalMeanFilterMethod/filter_kernel_size",
                label="filter kernel size",
                hasUnit=QUDT_UNIT.PIXEL,
                has_value=setting.filter_kernel_size
            )
        ]
    )

    multi_grid = pivmeta.Multigrid(
        parameter=[
            m4i.NumericalVariable(
                id=f"{base_uri}#Multigrid/initial_interrogation_window_size",
                label="initial interrogation window size",
                hasUnit=QUDT_UNIT.PIXEL,
                has_value=setting.windowsizes[0],
            ),
            m4i.NumericalVariable(
                id=f"{base_uri}#Multigrid/final_interrogation_window_size",
                label="final interrogation window size",
                hasUnit=QUDT_UNIT.PIXEL,
                has_value=setting.windowsizes[-1]
            ),
            m4i.NumericalVariable(
                id=f"{base_uri}#Multigrid/initial_interrogation_window_overlap",
                label="initial interrogation window overlap",
                hasUnit=QUDT_UNIT.PIXEL,
                has_value=setting.overlap[0]
            ),
            m4i.NumericalVariable(
                id=f"{base_uri}#Multigrid/final_interrogation_window_overlap",
                label="final interrogation window overlap",
                hasUnit=QUDT_UNIT.PIXEL,
                has_value=setting.overlap[-1]
            ),
            m4i.NumericalVariable(
                id=f"{base_uri}#Multigrid/num_iterations",
                label="number of multigrid iterations",
                hasUnit=QUDT_UNIT.UNITLESS,
                has_value=setting.num_iterations
            )
        ]
    )

    piv_evaluation = pivmeta.PIVEvaluation(
        id=f"{base_uri}#PIVEvaluation",
        hasEmployedTool=software,
        realizesMethod=[
            multi_grid,
            corr_method,
            sig2noise_method,
            filter_method,
        ]
    )
    if setting.dynamic_masking_method is not None:
        masking = Method(
            label="Masking Method",
            parameter=[
                NumericalVariable(
                    id=f"{base_uri}#MaskingMethod/dynamic_masking_method",
                    label="dynamic masking method",
                    hasUnit=QUDT_UNIT.PIXEL,
                    has_value=setting.dynamic_masking_threshold
                ),
                NumericalVariable(
                    id=f"{base_uri}#MaskingMethod/dynamic_masking_filter_size",
                    label="dynamic masking filter size",
                    hasUnit=QUDT_UNIT.PIXEL,
                    has_value=setting.dynamic_masking_filter_size
                )
            ]
        )
        piv_evaluation.realizesMethod.append(masking)

    virtual_setup = pivmeta.VirtualSetup(
        id=f"{base_uri}#VirtualSetup",
        usesSoftware=software
    )

    # combine both JSON-LD representations:
    merged_json = merge_jsonld([piv_evaluation.model_dump_jsonld(),
                                virtual_setup.model_dump_jsonld()])

    if fmt == "json-ld":
        output = merged_json
    else:
        g = rdflib.Graph()
        g.parse(data=merged_json, format='json-ld')
        output = g.serialize(format=fmt)
    with open(filename, 'w') as f:
        f.write(output)

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
