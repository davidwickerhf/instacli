class Progress():
    def __init__(self, bar, progress=None) -> None:
        self.bar = bar
        self.progress = progress

    def update_progress(self, new_progress):
        if not self.progress:
            self.progress = new_progress
            difference = new_progress
        else:
            difference = new_progress - self.progress
            self.progress = new_progress
        self.bar.update(difference)