from gi.repository import Gtk, GLib
import hashlib
import os
import collections
import threading
import Queue


class mainWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="DupDeleter")
        self.set_border_width(10)

        self.grid = Gtk.Grid()
        self.grid.set_column_homogeneous(True)
        self.grid.set_row_homogeneous(True)
        self.add(self.grid)

        # set up the model
        # columns = [imgName, imgLocation]
        self.dupe_store = Gtk.TreeStore(str, str)

        self.current_filter_ext = None
        self.ext_filter = self.dupe_store.filter_new()
        self.ext_filter.set_visible_func(self.ext_filter_func)

        self.treeview = Gtk.TreeView.new_with_model(self.ext_filter)
        for i, column_title in enumerate(["Name", "Location"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i)
            column.set_sort_column_id(i)
            self.treeview.append_column(column)

        self.scrollable_treelist = Gtk.ScrolledWindow()
        self.scrollable_treelist.set_vexpand(True)

        self.extensions = ("jpg", "gif", "png", "tiff", "All")

        self.buttons = list()
        for ext in self.extensions:
            button = Gtk.Button(ext)
            self.buttons.append(button)
            button.connect("clicked", self.on_selection_button_clicked)

        self.create_toolbar()

        self.file_scan_label = Gtk.Label(None)
        self.file_scan_label.set_text("This is a test")

        self.grid.attach(self.scrollable_treelist, 0, 1, 8, 10)
        self.grid.attach_next_to(self.buttons[0], self.scrollable_treelist,
            Gtk.PositionType.BOTTOM, 1, 1)
        for i, button in enumerate(self.buttons[1:]):
            self.grid.attach_next_to(button, self.buttons[i],
                Gtk.PositionType.RIGHT, 1, 1)
        self.scrollable_treelist.add(self.treeview)
        self.grid.attach_next_to(self.file_scan_label, self.buttons[0],
            Gtk.PositionType.BOTTOM, 8, 1)

        self.queue = Queue.Queue()  # Queue for holding fetched images

        self.show_all()

    def getDups(self, path, queue):
        '''Collects all image duplicates starting from PATH.
        Fills a queue with lists of lists 
        containing image names and locations.'''
        images = collections.defaultdict(list)
        image_exts = ('.jpg', '.png', '.gif', '.tiff')

        for root, dirs, files in os.walk(path):
            for name in files:
                GLib.idle_add(self.file_scan_label.set_text,
                 ("Scanning: " + root))
                if name[-4:] in image_exts:
                    img_loc = os.path.join(root, name)
                    img_data = open(img_loc).read()
                    img_hash = hashlib.md5(img_data).hexdigest()
                    images[img_hash].append([name, img_loc])

        GLib.idle_add(self.file_scan_label.set_text, "Done")

        for group in images:
            if len(images[group]) > 1:
                queue.put(images[group])

        GLib.idle_add(self.generateModelData)

    def generateModelData(self):
        '''Fills treeModel rows with found duplicates'''
        while not self.queue.empty():
            image_set = self.queue.get()
            parent = ''
            for img in image_set:
                if not parent:
                    parent = self.dupe_store.append(None, img)
                else:
                    self.dupe_store.append(parent, img)

    def on_button_clicked_open(self, widget):
        '''Brings up the file browser window.
        Returns the path of the root folder.'''
        dialog = Gtk.FileChooserDialog("Select the root folder", self,
                Gtk.FileChooserAction.SELECT_FOLDER,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                "Select", Gtk.ResponseType.OK))
        dialog.set_default_size(800, 400)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            root = dialog.get_uri()[8:]  # have to remove file:///
            thread = threading.Thread(target=self.getDups,
                args=(root, self.queue))
            thread.daemon = True
            thread.start()
            GLib.timeout_add(200, self.generateModelData)
            dialog.destroy()
        elif response == Gtk.ResponseType.CANCEL:
            dialog.destroy()

    def ext_filter_func(self, model, iter, data):
        '''Tests if the image extension in the row is the one in the filter'''
        if self.current_filter_ext is None or self.current_filter_ext == "All":
            return True
        else:
            return model[iter][0][-3:] == self.current_filter_ext

    def create_toolbar(self):
        toolbar = Gtk.Toolbar()
        self.grid.attach(toolbar, 0, 0, 8, 1)

        button_open = Gtk.ToolButton.new_from_stock(Gtk.STOCK_OPEN)
        toolbar.insert(button_open, 0)

        button_delete = Gtk.ToolButton.new_from_stock(Gtk.STOCK_DELETE)
        toolbar.insert(button_delete, 1)

        button_exit = Gtk.ToolButton.new_from_stock(Gtk.STOCK_QUIT)
        toolbar.insert(button_exit, 2)

        button_open.connect("clicked", self.on_button_clicked_open)
        button_delete.connect("clicked", self.on_button_clicked_delete)
        button_exit.connect("clicked", self.on_button_clicked_exit)

    def on_selection_button_clicked(self, widget):
        '''Called on any selection button click'''
        self.current_filter_ext = widget.get_label()
        self.ext_filter.refilter()

    def on_button_clicked_delete(self, widget):
        '''Deletes all selected files'''
        print "Files deleted"

    def on_button_clicked_exit(self, widget):
        '''Exits the program'''
        # Todo: add a confirmation dialog
        Gtk.main_quit()

win = mainWindow()
win.connect("delete-event", Gtk.main_quit)
win.show_all()
Gtk.main()
