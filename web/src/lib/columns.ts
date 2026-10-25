// The columns of the tables of the settings: the service, its fields, its
// state and its action. The header and the rows share them.
export const SERVICE_COLUMNS =
  "grid grid-cols-[13rem_minmax(0,1fr)_10.5rem_6.5rem] items-center gap-x-4 px-4";

// The columns of the rows of a tab: the box, the poster, the title and its
// file, the new name, the status and the search.
export const ROW_COLUMNS =
  "grid grid-cols-[1.25rem_2.25rem_minmax(0,1.1fr)_minmax(0,1.2fr)_6rem_2rem] items-center gap-x-3.5 px-4";

// The columns of the history: the chevron, the time, the type, the files, the
// file mode, the status and the undo.
export const OPERATION_COLUMNS =
  "grid grid-cols-[1rem_4.5rem_9rem_minmax(0,1fr)_minmax(0,11rem)_9rem_6.5rem] items-center gap-x-3.5 px-4";

// The columns of the files already processed: the box, the file, its new
// name and the date.
export const PROCESSED_COLUMNS =
  "grid grid-cols-[1.25rem_minmax(0,1fr)_minmax(0,1fr)_8rem] items-center gap-x-3.5 px-4";
