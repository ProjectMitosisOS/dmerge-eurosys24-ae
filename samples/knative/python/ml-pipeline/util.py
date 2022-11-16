def fill_ce_header(id, ce_specversion, ce_type, ce_source):
    """
    Fill for the Cloud Event header
    :param id:
    :param ce_specversion:
    :param ce_type:
    :param ce_source:
    :return:
    """
    return {
        "Ce-Id": id,
        "Ce-specversion": ce_specversion,
        "Ce-Type": ce_type,
        "Ce-Source": ce_source,
    }


