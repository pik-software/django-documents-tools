class ObservableInstanceRequiredError(Exception):
    pass


class SnapshotDuplicateExistsError(Exception):
    pass


class ChangesAreNotCreatedYetError(Exception):
    pass


class BusinessEntityCreationIsNotAllowedError(Exception):
    pass
