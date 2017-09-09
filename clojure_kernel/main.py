from metakernel._metakernel import MetaKernelApp

from .kernel import ClojureKernel

def main():
    """
    Launch the kernel.

    use meta kernel app so that `install` subcommand will properly install
    this package
    from https://github.com/Calysto/metakernel/blob/1a1cf358f3f716ec3098140e1fb766bb9938e68f/metakernel/_metakernel.py#L691
    won't need when this passes
    https://github.com/ipython/ipykernel/issues/196
    """
    MetaKernelApp.launch_instance(kernel_class=ClojureKernel)
