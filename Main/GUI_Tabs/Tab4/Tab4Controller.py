class Tab4Controller:
    def __init__(self, tab_frame, heavy_job=None):
        self.tab = tab_frame
        self.heavy_job = heavy_job

        #plot frame
        self.plot_frame = None

        #files
        self.file = None
        self.directory_path = None
        self.filename = None
        self.export_folder = None