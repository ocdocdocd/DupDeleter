from gi.repository import Gtk, GdkPixbuf, GLib, Pango
import dhash
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
        # columns = [imgName, imgLocation, # of Dups]
        self.dupe_store = Gtk.TreeStore(bool, str, str, int)

        self.current_filter_ext = None
        self.ext_filter = self.dupe_store.filter_new()
        self.ext_filter.set_visible_func(self.ext_filter_func)

        # Create model's view
        self.treeview = Gtk.TreeView.new_with_model(self.ext_filter)
        check_renderer = Gtk.CellRendererToggle()
        check_renderer.set_activatable(True)
        check_renderer.set_active(False)
        check_renderer.connect("toggled", self.on_toggled)
        column = Gtk.TreeViewColumn("", check_renderer, active=0)
        self.treeview.append_column(column)
        for i, column_title in enumerate(["Name", "Location", "# of Dups"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(column_title, renderer, text=i+1)
            column.set_sort_column_id(i)
            column.set_fixed_width(200)
            column.set_resizable(True)
            self.treeview.append_column(column)
        self.treeview.connect("cursor-changed", self.on_row_changed)

        self.scrollable_treelist = Gtk.ScrolledWindow()
        self.scrollable_treelist.set_vexpand(True)

        # Create buttons for filtering results by image extension
        self.extensions = ("jpg", "gif", "png", "tiff", "All")
        self.buttons = list()
        for ext in self.extensions:
            button = Gtk.Button(ext)
            self.buttons.append(button)
            button.connect("clicked", self.on_selection_button_clicked)

        self.create_toolbar()

        # Create labels for showing scan progress
        self.scan_status_label = Gtk.Label("No Scan in Progress")
        self.scan_status_label.set_halign(3)  # 3 = CENTER

        self.file_scan_label = Gtk.Label(None)
        self.file_scan_label.set_ellipsize(Pango.EllipsizeMode.START)
        self.file_scan_label.set_width_chars(30)
        self.file_scan_label.set_halign(3)  # 3 = CENTER

        # Make a frame to hold image previews
        self.img_frame = Gtk.Frame(label="Selected Image")
        self.img_frame.set_label_align(0.5, 0.5)
        self.img_frame.set_shadow_type(Gtk.ShadowType.ETCHED_OUT)
        self.img_frame.set_size_request(200, 200)

        # Assemble the GUI
        self.grid.attach(self.scrollable_treelist, 0, 1, 8, 10)
        self.grid.attach_next_to(self.img_frame, self.scrollable_treelist,
                                 Gtk.PositionType.RIGHT, 5, 6)
        self.grid.attach_next_to(self.buttons[0], self.scrollable_treelist,
                                 Gtk.PositionType.BOTTOM, 1, 1)
        for i, button in enumerate(self.buttons[1:]):
            self.grid.attach_next_to(button, self.buttons[i],
                                     Gtk.PositionType.RIGHT, 1, 1)
        self.scrollable_treelist.add(self.treeview)
        self.grid.attach_next_to(self.scan_status_label, self.buttons[3],
                                 Gtk.PositionType.BOTTOM, 6, 1)
        self.grid.attach_next_to(self.file_scan_label, self.scan_status_label,
                                 Gtk.PositionType.BOTTOM, 6, 1)
        self.grid.set_column_spacing(10)
        self.grid.set_row_spacing(5)

        self.queue = Queue.Queue()  # Queue for holding fetched images
        self.delete_list = list()  # List for holding to-be-deleted items

        self.show_all()

    def getDups(self, path, queue):
        '''Collects all image duplicates starting from PATH.
        Fills a queue with lists of lists
        containing image names and locations.'''
        images = collections.defaultdict(list)
        image_exts = ('.jpg', '.png', '.gif', '.tiff')

        GLib.idle_add(self.scan_status_label.set_text, "Scanning...")

        for root, dirs, files in os.walk(path):
            for name in files:
                GLib.idle_add(self.file_scan_label.set_text,
                              root)
                if name[-4:] in image_exts:
                    img_loc = os.path.join(root, name)
                    # img_data = open(img_loc).read()
                    img_hash = dhash.hash(img_loc)
                    if img_hash != -1:
                        # Have to add False at beginning because of
                        # togglebutton status.
                        images[img_hash].append([False, name, root])

        GLib.idle_add(self.scan_status_label.set_text, "Done")

        for group in images:
            if len(images[group]) > 1:
                queue.put(images[group])

        GLib.idle_add(self.generateModelData)

    def generateModelData(self):
        '''Fills treeModel rows with found duplicates'''
        while not self.queue.empty():
            image_set = self.queue.get()
            parent = ''
            no_of_dups = len(image_set)
            for img in image_set:
                img.append(no_of_dups)
                if not parent:
                    parent = self.dupe_store.append(None, img)
                else:
                    self.dupe_store.append(parent, img)

    def on_button_clicked_open(self, widget):
        '''Brings up the file browser window.
        Returns the path of the root folder.'''
        dialog = Gtk.FileChooserDialog("Select the root folder", self,
                                       Gtk.FileChooserAction.SELECT_FOLDER,
                                       (Gtk.STOCK_CANCEL,
                                        Gtk.ResponseType.CANCEL,
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
        button_open.set_tooltip_text("Scan Directory")
        toolbar.insert(button_open, 0)

        button_delete = Gtk.ToolButton.new_from_stock(Gtk.STOCK_DELETE)
        button_delete.set_tooltip_text("Delete Selected Images")
        toolbar.insert(button_delete, 1)

        button_auto_prune = Gtk.ToolButton.new_from_stock(Gtk.STOCK_NO)
        button_auto_prune.set_tooltip_text("Auto-Prune")
        toolbar.insert(button_auto_prune, 2)

        button_exit = Gtk.ToolButton.new_from_stock(Gtk.STOCK_QUIT)
        button_exit.set_tooltip_text("Exit")
        toolbar.insert(button_exit, 3)

        button_open.connect("clicked", self.on_button_clicked_open)
        button_auto_prune.connect("clicked", self.on_button_clicked_auto_prune)
        button_delete.connect("clicked", self.on_button_clicked_delete)
        button_exit.connect("clicked", self.on_button_clicked_exit)

    def on_selection_button_clicked(self, widget):
        '''Called on any selection button click'''
        self.current_filter_ext = widget.get_label()
        self.ext_filter.refilter()

    def on_button_clicked_auto_prune(self, widget):
        '''
        Automatically deletes all files except for parents
        '''
        dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.WARNING,
                                   Gtk.ButtonsType.OK_CANCEL,
                                   "Delete all selected images?")
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            rootiter = self.dupe_store.get_iter_first()
            deleted = self.prune_helper(rootiter, False)
            print "%d files deleted" % deleted
        elif response == Gtk.ResponseType.CANCEL:
            dialog.destroy()

    def prune_helper(self, treeiter, toDelete):
        '''
        Deletes all files except for parents

        toDelete indicates whether or not treeiter should be deleted.
        It should be set to False on call unless you want to delete
        everything.
        '''
        deleted = 0
        isValid = True
        while (treeiter is not None) and isValid:
            if self.dupe_store.iter_has_child(treeiter):
                childiter = self.dupe_store.iter_children(treeiter)
                deleted += self.prune_helper(childiter, True)
            if toDelete:
                path = os.path.join(self.dupe_store[treeiter][2],
                                    self.dupe_store[treeiter][1])
                os.remove(path)
                isValid = self.dupe_store.remove(treeiter)
                print "deleted %s" % path
                deleted += 1
            # If treestore.remove() is successful iter is automatically
            # updated to the next iter, so we just need to check to
            # make sure that isn't the case before using iter_next()
            else:
                treeiter = self.dupe_store.iter_next(treeiter)
        return deleted

    def on_button_clicked_delete(self, widget):
        '''Deletes all selected files'''
        dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.WARNING,
                                   Gtk.ButtonsType.OK_CANCEL,
                                   "Delete all selected images?")
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            rootiter = self.dupe_store.get_iter_first()
            deleted = self.delete_helper(rootiter)
            print "%d files deleted" % deleted
        elif response == Gtk. ResponseType.CANCEL:
            dialog.destroy()

    def delete_helper(self, treeiter):
        '''
        Recursively searches through all rows searching for files to
        delete.
        '''
        deleted = 0
        isValid = True
        while (treeiter is not None) and isValid:
            if self.dupe_store.iter_has_child(treeiter):
                childiter = self.dupe_store.iter_children(treeiter)
                deleted += self.delete_helper(childiter)
            if self.dupe_store[treeiter][0]:
                path = os.path.join(self.dupe_store[treeiter][2],
                                    self.dupe_store[treeiter][1])
                if self.dupe_store.iter_has_child(treeiter):
                    child = self.dupe_store.iter_children(treeiter)
                    isValid = self.childToParent(treeiter, child)
                else:
                    isValid = self.dupe_store.remove(treeiter)
                os.remove(path)
                print "deleted %s" % path
                deleted += 1
            else:
                treeiter = self.dupe_store.iter_next(treeiter)
        return deleted

    def on_button_clicked_exit(self, widget):
        '''Exits the program'''
        dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.WARNING,
                                   Gtk.ButtonsType.OK_CANCEL,
                                   "Are you sure you want to exit?")
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            Gtk.main_quit()
        elif response == Gtk.ResponseType.CANCEL:
            dialog.destroy()

    def childToParent(self, parent_iter, child_iter):
        '''
        Replaces parent_iter with child_iter, effectively moving child to
        parent's position.

        Returns the next iter after parent, or invalidates it if there
        isn't one.
        '''
        for col in xrange(self.dupe_store.get_n_columns()):
            childval = self.dupe_store.get_value(child_iter, col)
            self.dupe_store.set_value(parent_iter, col, childval)
        self.dupe_store.remove(child_iter)
        return self.dupe_store.iter_next(parent_iter)

    def on_row_changed(self, widget):
        (model, pathlist) = widget.get_selection().get_selected_rows()
        tree_iter = model.get_iter(pathlist[0])
        img_name = model.get_value(tree_iter, 1)
        img_root = model.get_value(tree_iter, 2)
        img_loc = os.path.join(img_root, img_name)
        # print img_loc
        child = self.img_frame.get_child()
        if child:
            self.img_frame.remove(child)
        alloc = self.img_frame.get_allocation()
        # print "alloc width is: %s" % alloc.width
        # print "alloc height is %s" % alloc.height
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(img_loc)
        width = pixbuf.get_width()
        height = pixbuf.get_height()
        ratio = float(width) / float(height)
        # print "ratio is %f" % ratio
        if width > alloc.width - 20:
            width = alloc.width - 20
        if height > alloc.height - 20:
            height = alloc.height - 20
        if ratio > 1.0:
            height = int(height / ratio)
            # print "height is %d" % height
        elif ratio < 1.0:
            width = int(width / ratio)
            # print "width is %d" % width
        pixbuf = pixbuf.scale_simple(width, height,
                                     GdkPixbuf.InterpType.BILINEAR)
        image = Gtk.Image.new_from_pixbuf(pixbuf)
        image.show()
        self.img_frame.add(image)

    def on_toggled(self, widget, path):
        '''
        Adds or removes the row's treeiter to a list that designates it
        for removal.
        '''
        self.dupe_store[path][0] = not self.dupe_store[path][0]


win = mainWindow()
win.connect("delete-event", Gtk.main_quit)
win.show_all()
Gtk.main()
